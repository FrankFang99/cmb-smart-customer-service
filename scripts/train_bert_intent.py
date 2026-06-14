"""
BERT 意图分类器 - 多模型 A/B 训练 (5 件套防过拟合)
==================================================
模型: M1=bert-tiny-chinese, M2=chinese-electra-180g-small, M3=bert-base-chinese
5 件套: 早停(patience=1) + 冻结后 6 层 + weight_decay 0.01 + dropout 0.3 + label smoothing 0.1
       + class weight (不平衡) + warmup 10% + cosine decay

输出: models/<model_short>/ (含 train_status.json 供 cron 监控)
"""
import os
import sys
import json
import time
import argparse
import math

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
os.environ["PYTHONIOENCODING"] = "utf-8"

import torch
torch.set_num_threads(8)
import numpy as np
from torch.optim import AdamW
from torch.nn import CrossEntropyLoss
from transformers import (
    BertTokenizer, BertForSequenceClassification, BertConfig,
    AutoTokenizer, AutoModelForSequenceClassification, AutoConfig,
    get_cosine_schedule_with_warmup,
)
from sklearn.model_selection import train_test_split

# ============== 模型注册表 ==============
MODEL_REGISTRY = {
    "M1": {
        "name": "bert-tiny-chinese",  # ~4M params
        "path": "models/M1-bert-tiny-chinese",
        "tokenizer": BertTokenizer,
        "model_cls": BertForSequenceClassification,
        "config_cls": BertConfig,
        "family": "bert",
    },
    "M2": {
        "name": "hfl/chinese-electra-180g-small-discriminator",  # ~12M params
        "path": "models/M2-electra-small",
        "tokenizer": AutoTokenizer,
        "model_cls": AutoModelForSequenceClassification,
        "config_cls": AutoConfig,
        "family": "electra",
    },
    "M3": {
        "name": "bert-base-chinese",  # ~102M params (已下载)
        "path": "models/M3-bert-base-chinese",
        "tokenizer": BertTokenizer,
        "model_cls": BertForSequenceClassification,
        "config_cls": BertConfig,
        "family": "bert",
    },
}

DATA_PATH = os.path.join(PROJECT_ROOT, "data", "evaluation_dataset_v8.0.json")


def write_status(out_dir: str, stage: str, **kwargs):
    status = {"stage": stage, "ts": time.time(), "pid": os.getpid(), **kwargs}
    os.makedirs(out_dir, exist_ok=True)
    sp = os.path.join(out_dir, "train_status.json")
    with open(sp, "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)
    kv = {k: round(v, 4) if isinstance(v, float) and abs(v) < 100 else v for k, v in kwargs.items() if not isinstance(v, list)}
    print(f"[STATUS] {stage} {json.dumps(kv, ensure_ascii=False)}", flush=True)


def load_data(label2id):
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        ds = json.load(f)
    train = [s for s in ds["samples"] if s.get("split") == "train"]
    holdout = [s for s in ds["samples"] if s.get("split") == "holdout"]
    def to_xy(samples):
        texts, labels = [], []
        for s in samples:
            t = s.get("text") or s.get("question", "")
            if not t or s["intent"] not in label2id:
                continue
            texts.append(t)
            labels.append(label2id[s["intent"]])
        return texts, labels
    return to_xy(train), to_xy(holdout)


def compute_class_weights(labels, n_classes):
    """反频率权重: 样本少的类权重高"""
    counts = np.bincount(labels, minlength=n_classes)
    weights = (counts.sum() / (n_classes * counts + 1e-6))
    weights = weights / weights.mean()  # 归一化到 mean=1
    return torch.tensor(weights, dtype=torch.float32)


def freeze_lower_layers(model, n_freeze: int, family: str):
    """冻结 BERT/electra 的前 n_freeze 层 encoder (业界标配: 全冻 M1/M2, 冻一半 M3)"""
    if family == "bert":
        for p in model.bert.embeddings.parameters():
            p.requires_grad = False
        for i in range(n_freeze):
            for p in model.bert.encoder.layer[i].parameters():
                p.requires_grad = False
    elif family == "electra":
        for p in model.electra.embeddings.parameters():
            p.requires_grad = False
        for i in range(n_freeze):
            for p in model.electra.encoder.layer[i].parameters():
                p.requires_grad = False
    n_trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    n_total = sum(p.numel() for p in model.parameters())
    print(f"  冻结前 {n_freeze} 层: trainable={n_trainable/1e6:.1f}M/{n_total/1e6:.1f}M ({100*n_trainable/n_total:.0f}%)", flush=True)


def train_with_overfit_guard(model, tokenizer, train_texts, train_labels, val_texts, val_labels,
                              test_texts, test_labels, n_classes, out_dir, family,
                              epochs=3, batch_size=16, lr=2e-5, max_len=16,
                              weight_decay=0.01, dropout=0.3, label_smoothing=0.1,
                              n_freeze=0, early_stop_patience=1, device="cpu"):
    """训练 + 早停 + 5 件套"""
    # 调 dropout (只对 classifier, encoder 保持预训练 dropout)
    if hasattr(model, "classifier") and hasattr(model.classifier, "dropout"):
        model.classifier.dropout = torch.nn.Dropout(dropout)

    # 5. Class weight (类不平衡)
    class_weights = compute_class_weights(train_labels, n_classes).to(device)
    print(f"  class_weights 范围: {float(class_weights.min()):.2f} - {float(class_weights.max()):.2f} (mean=1.0)", flush=True)

    # Loss = CE + label smoothing
    loss_fn = CrossEntropyLoss(weight=class_weights, label_smoothing=label_smoothing)

    # Optimizer (只优化 requires_grad=True 的)
    trainable_params = [p for p in model.parameters() if p.requires_grad]
    optimizer = AdamW(trainable_params, lr=lr, weight_decay=weight_decay)

    n_steps = (len(train_texts) // batch_size) * epochs
    scheduler = get_cosine_schedule_with_warmup(optimizer, int(n_steps * 0.1), n_steps)

    print(f"  训练: epochs={epochs}, batch={batch_size}, lr={lr}, max_len={max_len}", flush=True)
    print(f"  5件套: wd={weight_decay}, dropout={dropout}, label_smooth={label_smoothing}, freeze={n_freeze}层, early_stop_patience={early_stop_patience}", flush=True)
    print(f"  total_steps={n_steps}", flush=True)

    best_val_acc = 0.0
    best_epoch = 0
    no_improve = 0
    t0 = time.time()
    for epoch in range(1, epochs + 1):
        model.train()
        perm = np.random.permutation(len(train_texts))
        ep_loss, n_batches = 0.0, 0
        ep_t0 = time.time()
        for i in range(0, len(train_texts), batch_size):
            idx = perm[i:i + batch_size]
            batch_texts = [train_texts[j] for j in idx]
            batch_labels = torch.tensor([train_labels[j] for j in idx], dtype=torch.long).to(device)
            enc = tokenizer(batch_texts, return_tensors="pt", truncation=True, max_length=max_len, padding="max_length")
            enc = {k: v.to(device) for k, v in enc.items() if v is not None}
            optimizer.zero_grad()
            out = model(**enc)
            loss = loss_fn(out.logits, batch_labels)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            ep_loss += loss.item()
            n_batches += 1
        avg_loss = ep_loss / max(n_batches, 1)

        # Eval val
        model.eval()
        correct, total = 0, 0
        with torch.no_grad():
            for i in range(0, len(val_texts), batch_size):
                enc = tokenizer(val_texts[i:i + batch_size], return_tensors="pt", truncation=True, max_length=max_len, padding="max_length")
                enc = {k: v.to(device) for k, v in enc.items() if v is not None}
                labels = torch.tensor(val_labels[i:i + batch_size], dtype=torch.long).to(device)
                out = model(**enc)
                preds = out.logits.argmax(dim=-1)
                correct += int((preds == labels).sum())
                total += len(labels)
        val_acc = correct / max(total, 1)

        ep_t = time.time() - ep_t0
        total_t = time.time() - t0
        print(f"  epoch {epoch}/{epochs} | loss={avg_loss:.4f} | val_acc={val_acc*100:.2f}% | ep={ep_t:.0f}s | total={total_t:.0f}s", flush=True)
        write_status(out_dir, f"epoch_{epoch}_done", epoch=epoch, loss=avg_loss, val_acc=val_acc, ep_time=ep_t, total_time=total_t)

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            best_epoch = epoch
            no_improve = 0
            os.makedirs(out_dir, exist_ok=True)
            model.save_pretrained(out_dir)
            tokenizer.save_pretrained(out_dir)
            with open(os.path.join(out_dir, "label2id.json"), "w", encoding="utf-8") as f:
                json.dump({v: k for k, v in enumerate([s for s in set([*train_labels])])}, f, ensure_ascii=False, indent=2)  # placeholder, 下面会覆盖
            print(f"    -> saved (best so far: val_acc={val_acc*100:.2f}%)", flush=True)
            write_status(out_dir, f"epoch_{epoch}_saved", val_acc=val_acc)
        else:
            no_improve += 1
            print(f"    -> no improve ({no_improve}/{early_stop_patience})", flush=True)
            if no_improve >= early_stop_patience:
                print(f"  [EARLY STOP] patience={early_stop_patience} reached, stop at epoch {epoch}", flush=True)
                break

    # 最终 holdout
    model = model.__class__.from_pretrained(out_dir)
    model.to(device)
    model.eval()
    correct, total = 0, 0
    with torch.no_grad():
        for i in range(0, len(test_texts), batch_size):
            enc = tokenizer(test_texts[i:i + batch_size], return_tensors="pt", truncation=True, max_length=max_len, padding="max_length")
            enc = {k: v.to(device) for k, v in enc.items() if v is not None}
            labels = torch.tensor(test_labels[i:i + batch_size], dtype=torch.long).to(device)
            out = model(**enc)
            preds = out.logits.argmax(dim=-1)
            correct += int((preds == labels).sum())
            total += len(labels)
    holdout_acc = correct / max(total, 1)
    total_t = time.time() - t0
    print(f"\n  Final holdout_acc: {holdout_acc*100:.2f}%", flush=True)
    print(f"  best val_acc:     {best_val_acc*100:.2f}% (epoch {best_epoch})", flush=True)
    print(f"  total time:       {total_t:.0f}s ({total_t/60:.1f}min)", flush=True)
    write_status(out_dir, "done", val_acc=best_val_acc, holdout_acc=holdout_acc, best_epoch=best_epoch, total_time=total_t)
    return {"val_acc": best_val_acc, "holdout_acc": holdout_acc, "best_epoch": best_epoch, "total_time": total_t}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=list(MODEL_REGISTRY.keys()), default="M1")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch_size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=5e-5)
    parser.add_argument("--max_len", type=int, default=16)
    parser.add_argument("--n_freeze", type=int, default=0)
    parser.add_argument("--early_stop_patience", type=int, default=1)
    parser.add_argument("--weight_decay", type=float, default=0.01)
    parser.add_argument("--dropout", type=float, default=0.3)
    parser.add_argument("--label_smoothing", type=float, default=0.1)
    args = parser.parse_args()

    cfg = MODEL_REGISTRY[args.model]
    out_dir = os.path.join(PROJECT_ROOT, cfg["path"])
    model_name = cfg["name"]
    family = cfg["family"]
    model_local = os.path.join(PROJECT_ROOT, "models", "bert-base-chinese")  # M3 已下载, M1/M2 走 hf-mirror

    # 准备模型路径: M3 用本地, M1/M2 让 from_pretrained 走 hf-mirror 自动下载
    if args.model == "M3":
        model_path = model_local
    else:
        model_path = model_name  # 走 HF 镜像下载

    print("=" * 70, flush=True)
    print(f"训练 {args.model}: {model_name}", flush=True)
    print(f"  out: {out_dir}", flush=True)
    print("=" * 70, flush=True)
    write_status(out_dir, "loading_data")

    # 1. 数据
    label2id_path = os.path.join(PROJECT_ROOT, "models", "bert-intent-finetuned", "label2id.json")
    if not os.path.exists(label2id_path):
        # fallback: 临时从 v8 提取
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            ds = json.load(f)
        labels = sorted({s["intent"] for s in ds["samples"]})
        label2id = {l: i for i, l in enumerate(labels)}
        os.makedirs(os.path.dirname(label2id_path), exist_ok=True)
        with open(label2id_path, "w", encoding="utf-8") as f:
            json.dump(label2id, f, ensure_ascii=False, indent=2)
    else:
        with open(label2id_path, "r", encoding="utf-8") as f:
            label2id = json.load(f)
    print(f"  标签数: {len(label2id)}", flush=True)
    n_classes = len(label2id)

    (train_texts, train_labels), (test_texts, test_labels) = load_data(label2id)
    tr_texts, val_texts, tr_labels, val_labels = train_test_split(
        train_texts, train_labels, test_size=0.1, random_state=42, stratify=train_labels
    )
    print(f"  train={len(tr_texts)}, val={len(val_texts)}, test={len(test_texts)}", flush=True)

    # 2. 模型
    print(f"\n  加载 {model_path} ...", flush=True)
    t0 = time.time()
    tokenizer = cfg["tokenizer"].from_pretrained(model_path)
    model = cfg["model_cls"].from_pretrained(model_path, num_labels=n_classes)
    print(f"  加载耗时: {time.time()-t0:.1f}s", flush=True)

    # 验证权重真加载
    if family == "bert":
        encoder_std = float(model.bert.encoder.layer[0].attention.self.query.weight.std())
    else:
        encoder_std = float(model.electra.encoder.layer[0].attention.self.query.weight.std())
    print(f"  encoder.layer.0.attention.std={encoder_std:.4f}", flush=True)

    # 写 label2id (新路径)
    with open(os.path.join(out_dir, "label2id.json"), "w", encoding="utf-8") as f:
        json.dump(label2id, f, ensure_ascii=False, indent=2)
    write_status(out_dir, "training_started", total_epochs=args.epochs, train_n=len(tr_texts), val_n=len(val_texts))

    # 3. 冻结
    if args.n_freeze > 0:
        freeze_lower_layers(model, args.n_freeze, family)

    # 4. 训练
    result = train_with_overfit_guard(
        model, tokenizer, tr_texts, tr_labels, val_texts, val_labels, test_texts, test_labels,
        n_classes, out_dir, family,
        epochs=args.epochs, batch_size=args.batch_size, lr=args.lr, max_len=args.max_len,
        weight_decay=args.weight_decay, dropout=args.dropout, label_smoothing=args.label_smoothing,
        n_freeze=args.n_freeze, early_stop_patience=args.early_stop_patience,
    )

    # 写 result 到 json
    result_path = os.path.join(out_dir, "result.json")
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump({"model": args.model, "model_name": model_name, **result}, f, ensure_ascii=False, indent=2)
    print(f"\n[OK] 结果: {result_path}", flush=True)


if __name__ == "__main__":
    main()
