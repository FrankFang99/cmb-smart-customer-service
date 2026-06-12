"""
v3.5.3 扩评测集 600 -> 1500 (2.5x) + train/holdout 拆分
======================================================

设计:
1. 基于 v5.1 真实 query, 用同义词 + 句式变换生成 900 条新样本
2. 1:1 保留原 600 条 (train=400, holdout=200)
3. 新增 900 条: train=600, holdout=300
4. 总计 1500: train=1000, holdout=500

种子: 42 (可复现)
意图分布: 按 v5.1 比例扩

为什么种子 42:
- 业界标准随机种子
- 可复现 (面试演示时再跑结果一致)

为什么 train 1000 / holdout 500 (2:1):
- 业界标准 70/30 或 2:1
- 1000 足够大, 500 验证泛化
"""

from __future__ import annotations

import json
import random
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

_ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = _ROOT / "data" / "evaluation_dataset_v5.1.json"
OUTPUT_PATH = _ROOT / "data" / "evaluation_dataset_v6.0.json"

# 同义词表 (中文口语化扩展)
SYNONYM_DICT = {
    "我": ["我的", "我自己的", "俺", "咱"],
    "我的": ["我自己的", "本人的", "我这边的"],
    "怎么": ["如何", "怎样", "怎么弄", "怎么办"],
    "什么": ["啥", "哪个", "哪些"],
    "信用卡": ["招行信用卡", "信用卡卡", "招行卡", "信用卡子"],
    "账单": ["账", "消费", "花销", "用了多少"],
    "多少钱": ["多少", "几多", "多少块", "多钱"],
    "挂失": ["丢了", "丢失", "被偷", "不见了"],
    "激活": ["开卡", "开通", "启用", "激活用"],
    "转人工": ["找人工", "转真人", "真人客服", "要人工"],
    "你好": ["您好", "在吗", "hi", "哈喽"],
    "推荐": ["推", "建议", "有什么"],
    "贷款": ["借款", "借钱", "贷点款"],
    "理财": ["理财产品", "投资产品", "朝朝宝"],
}

# 句式变换模板
TEMPLATES = [
    lambda q: q,  # 原句
    lambda q: q + "?",  # 加问号
    lambda q: q + "？",  # 加中文问号
    lambda q: "请问" + q,  # 加请问
    lambda q: "那个" + q,  # 加那个
    lambda q: q + "谢谢",  # 加谢谢
    lambda q: "想问一下" + q,  # 加想问一下
    lambda q: q.replace("。", "").replace("?", "").replace("？", ""),  # 去标点
]


def synonym_replace(text: str, prob: float = 0.3) -> str:
    """同义词替换 (30% 概率)"""
    result = text
    for word, synonyms in SYNONYM_DICT.items():
        if word in result and random.random() < prob:
            syn = random.choice(synonyms)
            result = result.replace(word, syn, 1)
    return result


def apply_template(text: str) -> str:
    """应用随机句式模板"""
    template = random.choice(TEMPLATES)
    return template(text).strip()


def expand_samples(
    samples: List[Dict],
    target_count: int = 1500,
    seed: int = 42,
) -> List[Dict]:
    """
    扩样本到 target_count
    策略: 复用 + 同义词变换 + 句式变换
    """
    random.seed(seed)
    base_count = len(samples)
    if base_count >= target_count:
        return samples
    # 计算每条原样本需扩展多少次
    expand_factor = (target_count - base_count) // base_count + 1
    expanded = list(samples)  # 保留原 600 条
    next_id = base_count + 1
    for _ in range(expand_factor):
        for s in samples:
            if len(expanded) >= target_count:
                break
            new_q = synonym_replace(s["question"], prob=0.3)
            new_q = apply_template(new_q)
            # 同 intent + 同 is_p0, 但新 question
            new_sample = {
                "id": f"V6_{next_id:04d}",
                "intent": s["intent"],
                "question": new_q,
                "is_p0": s.get("is_p0", False),
                "source": "expanded_v5.1",
            }
            expanded.append(new_sample)
            next_id += 1
        if len(expanded) >= target_count:
            break
    return expanded


def split_train_holdout(
    samples: List[Dict],
    train_ratio: float = 0.67,
    seed: int = 42,
) -> List[Dict]:
    """
    train/holdout 拆分 (种子 42, 可复现)
    默认 2/3 train, 1/3 holdout
    """
    random.seed(seed)
    # 按意图分层抽样 (保证每意图 train/holdout 都有)
    by_intent: Dict[str, List[Dict]] = {}
    for s in samples:
        intent = s.get("intent", "unknown")
        by_intent.setdefault(intent, []).append(s)
    for intent in by_intent:
        random.shuffle(by_intent[intent])
    train, holdout = [], []
    for intent, items in by_intent.items():
        split = int(len(items) * train_ratio)
        train.extend(items[:split])
        holdout.extend(items[split:])
    # 标记 split
    for s in train:
        s["split"] = "train"
    for s in holdout:
        s["split"] = "holdout"
    # 合并并打散
    combined = train + holdout
    random.shuffle(combined)
    return combined


def main():
    print("=" * 60)
    print("v3.5.3 扩评测集 600 -> 1500 (2.5x) + train/holdout 拆分")
    print("=" * 60)
    # 加载 v5.1
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        v51 = json.load(f)
    base_samples = v51["samples"]
    print(f"v5.1 基础: {len(base_samples)} 样本")
    # 扩到 1500
    expanded = expand_samples(base_samples, target_count=1500, seed=42)
    print(f"扩展后: {len(expanded)} 样本 (+{len(expanded) - len(base_samples)})")
    # train/holdout 拆分
    split = split_train_holdout(expanded, train_ratio=0.67, seed=42)
    train_n = sum(1 for s in split if s.get("split") == "train")
    holdout_n = sum(1 for s in split if s.get("split") == "holdout")
    print(f"train: {train_n}, holdout: {holdout_n}")
    # 分布统计
    grp_count = Counter(s.get("intent", "unknown").split("_")[0] for s in split)
    p0_count = sum(1 for s in split if s.get("is_p0", False))
    print(f"P0: {p0_count} ({p0_count/len(split)*100:.1f}%)")
    print(f"业务组: {dict(grp_count)}")
    # 输出
    output = {
        "dataset_version": "v6.0",
        "total_samples": len(split),
        "generated_date": "2026-06-12",
        "description": "v5.1 同分布扩展 (1500 样本) + train/holdout 拆分 (1000/500) - 种子 42 可复现",
        "base_dataset": "evaluation_dataset_v5.1.json",
        "expansion_method": "同义词替换 + 句式模板",
        "train_count": train_n,
        "holdout_count": holdout_n,
        "samples": split,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n输出: {OUTPUT_PATH}")
    print(f"\n前 3 条样本:")
    for s in split[:3]:
        print(f"  [{s.get('split'):7s}] {s['id']} | intent={s['intent']:20s} | Q: {s['question']}")


if __name__ == "__main__":
    main()
