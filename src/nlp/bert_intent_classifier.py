"""
BERT 意图分类器 (CPU 微调 + 推理)
============================
- 模型: bert-base-chinese (110MB, HuggingFace)
- 输入: 中文 query (max_len=32)
- 输出: 30 个意图之一 + softmax 概率
- 微调: 3 epoch, batch_size=32, lr=2e-5
- 推理: ~50ms / query (CPU)

业界对齐: 招行 2024 招行智能客服年报 / 工行"工小智" / 蚂蚁金服保险客服
"""
from __future__ import annotations
import os
import json
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import List, Tuple, Dict, Optional
from transformers import BertTokenizer, BertForSequenceClassification

# 模型保存路径 (项目本地, 不下载到 mavis 全局)
BERT_MODEL_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "models", "bert-base-chinese"
)
FINETUNED_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "models", "bert-intent-finetuned"
)
LABEL2ID_PATH = os.path.join(FINETUNED_DIR, "label2id.json")


def load_label2id() -> Dict[str, int]:
    """从评测集提取所有意图 label2id 映射 (训练/推理必须一致)"""
    if os.path.exists(LABEL2ID_PATH):
        with open(LABEL2ID_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    # 默认: 从 v8.0 评测集提取
    ds_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "data", "evaluation_dataset_v8.0.json"
    )
    with open(ds_path, "r", encoding="utf-8") as f:
        ds = json.load(f)
    labels = sorted({s["intent"] for s in ds["samples"]})
    label2id = {l: i for i, l in enumerate(labels)}
    os.makedirs(FINETUNED_DIR, exist_ok=True)
    with open(LABEL2ID_PATH, "w", encoding="utf-8") as f:
        json.dump(label2id, f, ensure_ascii=False, indent=2)
    return label2id


def id2label_map(label2id: Dict[str, int]) -> Dict[int, str]:
    return {v: k for k, v in label2id.items()}


class BertIntentClassifier:
    """BERT 意图分类器 (微调 + 推理)"""

    def __init__(
        self,
        model_dir: str = BERT_MODEL_DIR,
        num_labels: int = 30,
        max_len: int = 32,
    ):
        self.model_dir = model_dir
        self.num_labels = num_labels
        self.max_len = max_len
        self.tokenizer: Optional[BertTokenizer] = None
        self.model: Optional[BertForSequenceClassification] = None
        self.label2id: Optional[Dict[str, int]] = None
        self.id2label: Optional[Dict[int, str]] = None
        self._loaded = False

    def load_base(self) -> None:
        """加载预训练 bert-base-chinese (110MB)"""
        if not os.path.exists(self.model_dir):
            raise FileNotFoundError(
                f"BERT 模型未找到: {self.model_dir}\n"
                f"请先运行: python scripts/download_bert.py"
            )
        self.tokenizer = BertTokenizer.from_pretrained(self.model_dir)
        self.label2id = load_label2id()
        self.id2label = id2label_map(self.label2id)
        self.model = BertForSequenceClassification.from_pretrained(
            self.model_dir,
            num_labels=len(self.label2id),
        )
        self.model.eval()
        self._loaded = True

    def load_finetuned(self) -> None:
        """加载微调后的模型"""
        if not os.path.exists(FINETUNED_DIR):
            raise FileNotFoundError(
                f"微调模型未找到: {FINETUNED_DIR}\n"
                f"请先运行: python scripts/train_bert_intent.py"
            )
        self.tokenizer = BertTokenizer.from_pretrained(FINETUNED_DIR)
        with open(LABEL2ID_PATH, "r", encoding="utf-8") as f:
            self.label2id = json.load(f)
        self.id2label = id2label_map(self.label2id)
        self.model = BertForSequenceClassification.from_pretrained(FINETUNED_DIR)
        self.model.eval()
        self._loaded = True

    @torch.no_grad()
    def predict(self, text: str) -> Tuple[str, float, List[Tuple[str, float]]]:
        """
        预测单条 query
        Returns:
            (intent, confidence, top3 [(intent, prob), ...])
        """
        if not self._loaded:
            self.load_finetuned()
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=self.max_len,
            padding="max_length",
        )
        outputs = self.model(**inputs)
        logits = outputs.logits[0]
        probs = F.softmax(logits, dim=-1).cpu().numpy()
        top3_idx = probs.argsort()[-3:][::-1]
        top3 = [(self.id2label[int(i)], float(probs[i])) for i in top3_idx]
        intent = top3[0][0]
        confidence = top3[0][1]
        return intent, confidence, top3

    @torch.no_grad()
    def predict_batch(self, texts: List[str], batch_size: int = 64) -> List[Tuple[str, float]]:
        """批量预测"""
        if not self._loaded:
            self.load_finetuned()
        results = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            inputs = self.tokenizer(
                batch,
                return_tensors="pt",
                truncation=True,
                max_length=self.max_len,
                padding="max_length",
            )
            outputs = self.model(**inputs)
            probs = F.softmax(outputs.logits, dim=-1).cpu().numpy()
            preds = probs.argmax(axis=-1)
            for j, p in enumerate(preds):
                results.append((self.id2label[int(p)], float(probs[j, p])))
        return results


def collate_batch(tokenizer, texts, labels, max_len):
    """手写 collate_fn, 不依赖 datasets"""
    enc = tokenizer(
        texts,
        return_tensors="pt",
        truncation=True,
        max_length=max_len,
        padding="max_length",
    )
    return {
        "input_ids": enc["input_ids"],
        "attention_mask": enc["attention_mask"],
        "token_type_ids": enc.get("token_type_ids"),
        "labels": torch.tensor(labels, dtype=torch.long),
    }


def train_one_epoch(model, tokenizer, train_texts, train_labels, optimizer, scheduler, batch_size, max_len, device):
    """手写 1 个 epoch 训练循环 (不依赖 Trainer)"""
    model.train()
    total_loss = 0.0
    n_batches = 0
    n = len(train_texts)
    # 简单 shuffle
    perm = np.random.permutation(n)
    for i in range(0, n, batch_size):
        idx = perm[i:i + batch_size]
        batch = collate_batch(tokenizer, [train_texts[j] for j in idx], [train_labels[j] for j in idx], max_len)
        batch = {k: v.to(device) if v is not None else None for k, v in batch.items()}
        optimizer.zero_grad()
        outputs = model(**batch)
        loss = outputs.loss
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        if scheduler is not None:
            scheduler.step()
        total_loss += loss.item()
        n_batches += 1
    return total_loss / max(n_batches, 1)


@torch.no_grad()
def eval_model(model, tokenizer, val_texts, val_labels, batch_size, max_len, device):
    """手写 eval"""
    model.eval()
    correct = 0
    total = 0
    for i in range(0, len(val_texts), batch_size):
        batch = collate_batch(tokenizer, val_texts[i:i + batch_size], val_labels[i:i + batch_size], max_len)
        batch = {k: v.to(device) if v is not None else None for k, v in batch.items()}
        outputs = model(**batch)
        preds = outputs.logits.argmax(dim=-1).cpu().numpy()
        labels = batch["labels"].cpu().numpy()
        correct += int((preds == labels).sum())
        total += len(labels)
    return correct / max(total, 1)
