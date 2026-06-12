"""
v3.5.4 真 LLM 评测 - 3560 样本 (种子问题扩展 + train/holdout 拆分)
================================================================

关键改进:
- v3.5.4-2: e2e_pipeline._build_system_prompt 注入 v3.5.1 L0 词典 14 词
  (让 cascade L3 LLM 兜底也认这些 P0 关键词, 提升 P0 Recall)
- 3560 样本 (v6.0 1500 + 种子扩展 2060) + train/holdout 拆分
- 重点: P0 Recall 是核心指标 (银行业 P0 红线)

输入: data/evaluation_dataset_v7.0.json
输出: data/eval_results_v354.json
"""

from __future__ import annotations

import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Any

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.agent.e2e_pipeline import create_e2e_pipeline
from src.components.intent_recognizer import IntentRecognizer


DATASET_PATH = _ROOT / "data" / "evaluation_dataset_v7.0.json"
OUTPUT_PATH = _ROOT / "data" / "eval_results_v354.json"


def evaluate_sample(pipeline, sample: Dict) -> Dict:
    question = sample["question"]
    expected_intent = sample["intent"]
    is_p0_label = sample.get("is_p0", False)

    t0 = time.time()
    try:
        e2e = pipeline.handle(question, session_id=f"eval_{sample['id']}")
    except Exception as e:
        return {
            "sample_id": sample["id"],
            "question": question,
            "expected_intent": expected_intent,
            "is_p0_label": is_p0_label,
            "split": sample.get("split", "unknown"),
            "error": str(e),
            "intent_match": False,
            "p0_recall": False,
            "l0_compliance": False,
            "rag_hit": False,
            "transfer_correct": False,
            "elapsed_ms": 0,
        }
    t_total = (time.time() - t0) * 1000

    actual_intent = e2e.get("intent", "unknown")
    intent_match = actual_intent == expected_intent
    p0_recall = e2e.get("l0_triggered", False) if is_p0_label else None
    if e2e.get("l0_triggered"):
        l0_compliance = e2e.get("action") == "transfer_human" and "llm_elapsed_ms" not in e2e
    else:
        l0_compliance = None
    rag_hit = False
    if not e2e.get("l0_triggered"):
        rag_hit = len(e2e.get("sources", [])) > 0
    if is_p0_label:
        transfer_correct = e2e.get("action") == "transfer_human"
    else:
        transfer_correct = e2e.get("action") == "answer"

    return {
        "sample_id": sample["id"],
        "question": question,
        "expected_intent": expected_intent,
        "actual_intent": actual_intent,
        "is_p0_label": is_p0_label,
        "split": sample.get("split", "unknown"),
        "intent_match": intent_match,
        "p0_recall": p0_recall,
        "l0_compliance": l0_compliance,
        "rag_hit": rag_hit,
        "transfer_correct": transfer_correct,
        "action": e2e.get("action"),
        "l0_triggered": e2e.get("l0_triggered", False),
        "elapsed_ms": round(t_total, 1),
    }


def aggregate_split(results: List[Dict]) -> Dict:
    total = len(results)
    if total == 0:
        return {"total": 0}
    intent_correct = sum(1 for r in results if r.get("intent_match"))
    p0_samples = [r for r in results if r.get("is_p0_label")]
    p0_recall = (
        sum(1 for r in p0_samples if r.get("p0_recall")) / len(p0_samples)
        if p0_samples else 1.0
    )
    l0_samples = [r for r in results if r.get("l0_triggered")]
    l0_compliance = (
        sum(1 for r in l0_samples if r.get("l0_compliance")) / len(l0_samples)
        if l0_samples else 1.0
    )
    non_l0_samples = [r for r in results if not r.get("l0_triggered")]
    rag_hit = (
        sum(1 for r in non_l0_samples if r.get("rag_hit")) / len(non_l0_samples)
        if non_l0_samples else 1.0
    )
    transfer_correct = sum(1 for r in results if r.get("transfer_correct"))
    transfer_accuracy = transfer_correct / total

    by_intent_group: Dict[str, Dict] = defaultdict(lambda: {"total": 0, "correct": 0})
    for r in results:
        group = r.get("expected_intent", "unknown").split("_")[0]
        by_intent_group[group]["total"] += 1
        if r.get("intent_match"):
            by_intent_group[group]["correct"] += 1
    for g in by_intent_group:
        if by_intent_group[g]["total"]:
            by_intent_group[g]["accuracy"] = round(
                by_intent_group[g]["correct"] / by_intent_group[g]["total"], 4
            )

    # P0 详细分析
    p0_by_intent: Dict[str, Dict] = defaultdict(lambda: {"total": 0, "recalled": 0})
    for r in results:
        if r.get("is_p0_label"):
            intent = r.get("expected_intent", "unknown")
            p0_by_intent[intent]["total"] += 1
            if r.get("p0_recall"):
                p0_by_intent[intent]["recalled"] += 1
    for k in p0_by_intent:
        if p0_by_intent[k]["total"]:
            p0_by_intent[k]["recall"] = round(
                p0_by_intent[k]["recalled"] / p0_by_intent[k]["total"], 4
            )

    return {
        "total": total,
        "intent_accuracy": round(intent_correct / total, 4),
        "p0_recall": round(p0_recall, 4),
        "l0_compliance": round(l0_compliance, 4),
        "rag_hit_rate": round(rag_hit, 4),
        "transfer_accuracy": round(transfer_accuracy, 4),
        "p0_samples": len(p0_samples),
        "l0_triggered": len(l0_samples),
        "by_intent_group": dict(by_intent_group),
        "p0_by_intent": dict(p0_by_intent),
    }


def main():
    print("=" * 80)
    print("v3.5.4 真 LLM 评测 - 3560 样本 + L0 Prompt 注入修复")
    print("=" * 80)

    with open(DATASET_PATH, encoding="utf-8") as f:
        dataset = json.load(f)
    samples = dataset["samples"]
    print(f"数据集版本: {dataset['dataset_version']}, 总样本: {len(samples)}")
    print(f"train: {dataset.get('train_count')}, holdout: {dataset.get('holdout_count')}")
    print(f"P0: {dataset.get('p0_count')} ({dataset.get('p0_count', 0)/len(samples)*100:.1f}%)")
    print()

    pipeline = create_e2e_pipeline(k=3)
    intent_recognizer = IntentRecognizer()

    all_results = []
    t0 = time.time()
    total_n = len(samples)
    for i, sample in enumerate(samples, 1):
        if i % 100 == 0 or i == 1:
            elapsed = time.time() - t0
            eta = (elapsed / i) * (total_n - i) if i > 0 else 0
            print("  [%d/%d] (%.0f%%)  已用 %.0fs, 预计剩余 %.0fs" % (
                i, total_n, i/total_n*100, elapsed, eta))
        all_results.append(evaluate_sample(pipeline, sample))
    total_elapsed = time.time() - t0
    print("\n  跑完 %d 样本, 总耗时 %.1fs (%.1f 分钟)" % (total_n, total_elapsed, total_elapsed/60))

    train_results = [r for r in all_results if r.get("split") == "train"]
    holdout_results = [r for r in all_results if r.get("split") == "holdout"]
    overall = aggregate_split(all_results)
    train_summary = aggregate_split(train_results)
    holdout_summary = aggregate_split(holdout_results)

    print("\n" + "=" * 80)
    print("v3.5.4 真 LLM 评测结果 (train/holdout)")
    print("=" * 80)
    print("%-22s %-12s %-14s %-14s %-10s" % ("指标", "Overall", "Train", "Holdout", "泛化 Δ"))
    print("-" * 80)
    for metric in ("intent_accuracy", "p0_recall", "l0_compliance", "rag_hit_rate", "transfer_accuracy"):
        o = overall.get(metric, 0)
        t = train_summary.get(metric, 0)
        h = holdout_summary.get(metric, 0)
        delta = round(t - h, 4) if t and h else 0
        print("%-22s %6.2f%%      %6.2f%%        %6.2f%%        %+6.2fpp" % (
            metric, o*100, t*100, h*100, delta*100))
    print()

    # 与 v3.5.3 对比
    print("=" * 80)
    print("v3.5.3 (1500) / v3.5.4 (3560) 对比")
    print("=" * 80)
    print("%-22s %-12s %-14s %-18s" % ("指标", "v3.5.3 Hold", "v3.5.4 Hold", "Δ 修复提升"))
    print("-" * 80)
    v353_h = {"intent_accuracy": 0.8428, "p0_recall": 0.5270, "l0_compliance": 1.0, "rag_hit_rate": 0.9957}
    comparison = [
        ("intent_accuracy", v353_h["intent_accuracy"], holdout_summary["intent_accuracy"]),
        ("p0_recall", v353_h["p0_recall"], holdout_summary["p0_recall"]),
        ("l0_compliance", v353_h["l0_compliance"], holdout_summary["l0_compliance"]),
        ("rag_hit_rate", v353_h["rag_hit_rate"], holdout_summary["rag_hit_rate"]),
    ]
    for name, v353, v354 in comparison:
        delta = (v354 - v353) * 100
        print("%-22s %6.2f%%      %6.2f%%        %+6.2fpp" % (name, v353*100, v354*100, delta))

    # P0 详细
    print("\nP0 按意图详细 (holdout):")
    for intent, stat in sorted(holdout_summary["p0_by_intent"].items()):
        recall = stat.get("recall", 0) * 100
        print("  %-25s: %d/%d = %.1f%%" % (intent, stat["recalled"], stat["total"], recall))

    # 按业务分组
    print("\n按业务分组 (holdout):")
    for g, v in sorted(holdout_summary["by_intent_group"].items(), key=lambda x: -x[1]["total"]):
        print("  %-8s: %d/%d = %.1f%%" % (g, v["correct"], v["total"], v["accuracy"]*100))

    # 输出
    output = {
        "eval_version": "v3.5.4",
        "eval_date": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "llm": "MiniMax-M2.7 via api.minimaxi.com/v1 (订阅 Key)",
        "dataset_version": "v7.0",
        "patches_applied": "v3.5.4-2: e2e_pipeline L0 Prompt 注入 (v3.5.1 L0 词典 14 词 + 5 类 P0)",
        "summary": {
            "overall": overall,
            "train": train_summary,
            "holdout": holdout_summary,
        },
        "total_elapsed_ms": round(total_elapsed * 1000, 1),
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2, default=str)
    print("\n结果保存: %s" % OUTPUT_PATH)


if __name__ == "__main__":
    main()
