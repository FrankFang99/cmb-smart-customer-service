"""
v3.5.1 Badcase 修复评测 — 600 样本 + Badcase 池重测
====================================================

对比 v3.4.0:
- v3.4.0: 意图 83% / P0 Recall 50% / L0 Compliance 100% / RAG 98.75%
- v3.5.1: 预计意图 90% (+7pp) / P0 Recall 90% (+40pp) / L0 100%

为什么不调 LLM:
- v3.5.1 修复都是意图规则 (L0 词典 + 8 条规则), 0 LLM 调用
- 节省 token, 快速验证修复效果
- 修复后真实 LLM 跑分留 v4.0

输入: data/evaluation_dataset_v5.1.json (600 样本)
输出: data/eval_results_v351.json
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Any

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.components.intent_recognizer import IntentRecognizer


DATASET_PATH = _ROOT / "data" / "evaluation_dataset_v5.1.json"
OUTPUT_PATH = _ROOT / "data" / "eval_results_v351.json"


def evaluate_sample(intent_recognizer, sample: Dict) -> Dict:
    """
    单样本评测 (只调意图识别器, 不调 LLM)
    """
    t0 = time.time()
    question = sample.get("question", "")
    expected_intent = sample.get("intent", "") or sample.get("expected_intent", "")
    is_p0_label = sample.get("is_p0", False) or sample.get("is_p0_label", False)
    result = intent_recognizer.recognize(question)
    elapsed = (time.time() - t0) * 1000
    # 实际意图
    actual_intent = result.intent.value if hasattr(result.intent, "value") else str(result.intent)
    intent_match = actual_intent == expected_intent
    # P0 Recall: P0 样本是否触发 L0 (transfer)
    p0_recall = None
    if is_p0_label:
        p0_recall = result.is_p0 or result.should_transfer
    # L0 Compliance: L0 触发后 confidence > 0.7 (不答业务)
    l0_compliance = None
    if result.is_p0 or result.should_transfer:
        l0_compliance = result.confidence >= 0.7
    return {
        "sample_id": sample.get("id", sample.get("sample_id", "unknown")),
        "question": question,
        "expected_intent": expected_intent,
        "actual_intent": actual_intent,
        "is_p0_label": is_p0_label,
        "intent_match": intent_match,
        "p0_recall": p0_recall,
        "l0_compliance": l0_compliance,
        "is_p0_actual": result.is_p0,
        "should_transfer": result.should_transfer,
        "confidence": result.confidence,
        "reasoning": result.reasoning,
        "elapsed_ms": round(elapsed, 2),
    }


def main():
    print("=" * 60)
    print("v3.5.1 Badcase 修复评测 (0 LLM, 0 token)")
    print("=" * 60)
    # 加载数据
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        dataset = json.load(f)
    samples = dataset.get("samples", dataset) if isinstance(dataset, dict) else dataset
    print(f"数据集: {len(samples)} 样本")
    # 评测
    intent_recognizer = IntentRecognizer()
    sample_results = []
    p0_label_count = 0
    t0 = time.time()
    for i, sample in enumerate(samples):
        if i % 100 == 0:
            print(f"  [{i}/{len(samples)}]")
        if sample.get("is_p0") or sample.get("is_p0_label"):
            p0_label_count += 1
        sample_results.append(evaluate_sample(intent_recognizer, sample))
    total_elapsed = time.time() - t0
    # 统计
    intent_correct = sum(1 for r in sample_results if r["intent_match"])
    intent_accuracy = intent_correct / len(sample_results)
    p0_samples = [r for r in sample_results if r["is_p0_label"]]
    p0_recall = (
        sum(1 for r in p0_samples if r["p0_recall"]) / len(p0_samples)
        if p0_samples else 1.0
    )
    l0_triggered = [r for r in sample_results if r["is_p0_actual"] or r["should_transfer"]]
    l0_compliance = (
        sum(1 for r in l0_triggered if r["l0_compliance"]) / len(l0_triggered)
        if l0_triggered else 1.0
    )
    # 按业务分组
    by_intent_group: Dict[str, Dict[str, int]] = defaultdict(lambda: {"total": 0, "correct": 0})
    for r in sample_results:
        grp = r["expected_intent"].split("_")[0] if r["expected_intent"] else "unknown"
        by_intent_group[grp]["total"] += 1
        if r["intent_match"]:
            by_intent_group[grp]["correct"] += 1
    by_intent_group = {
        g: {
            "total": v["total"],
            "correct": v["correct"],
            "accuracy": round(v["correct"] / v["total"], 4) if v["total"] else 0,
        }
        for g, v in by_intent_group.items()
    }
    failures = [r for r in sample_results if not r["intent_match"]]
    summary = {
        "eval_version": "v3.5.1",
        "eval_date": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "llm": "无 (0 LLM, 只跑意图规则)",
        "dataset_version": "v5.1",
        "summary": {
            "total_samples": len(sample_results),
            "intent_accuracy": round(intent_accuracy, 4),
            "p0_recall": round(p0_recall, 4),
            "l0_compliance": round(l0_compliance, 4),
            "p0_label_count": p0_label_count,
            "l0_triggered_count": len(l0_triggered),
            "by_intent_group": dict(by_intent_group),
            "failures_count": len(failures),
            "total_elapsed_ms": round(total_elapsed * 1000, 1),
            "avg_elapsed_ms": round(total_elapsed * 1000 / len(sample_results), 2),
        },
        "sample_results": sample_results,
    }
    # 输出
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print("\n" + "=" * 60)
    print("v3.5.1 评测结果")
    print("=" * 60)
    print(f"总样本数: {len(sample_results)}")
    print(f"意图准确率: {intent_accuracy*100:.2f}%  (v3.4.0 = 83%, +{intent_accuracy*100-83:.2f}pp)")
    print(f"P0 Recall:  {p0_recall*100:.2f}%  (v3.4.0 = 50%, +{p0_recall*100-50:.2f}pp)")
    print(f"L0 Compliance: {l0_compliance*100:.2f}%  (v3.4.0 = 100%)")
    print(f"L0 触发数: {len(l0_triggered)}  (v3.4.0 = 42)")
    print(f"失败样本: {len(failures)}  (v3.4.0 = 13)")
    print(f"总耗时: {total_elapsed:.1f}s  (v3.4.0 = 221s 含 LLM)")
    print()
    print("按业务分组:")
    for g, v in sorted(by_intent_group.items(), key=lambda x: -x[1]["total"]):
        print(f"  {g:8s}: {v['correct']}/{v['total']} = {v['accuracy']*100:.1f}%")
    print(f"\n结果已保存: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
