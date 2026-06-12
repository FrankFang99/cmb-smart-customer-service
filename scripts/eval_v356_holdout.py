"""
v3.5.6 真 LLM 评测 - 2567 holdout (修问候词模板 + 意图规则扩 20)
====================================================================

修复:
- v3.5.6-1: 模板去掉"你好"/"谢谢"前缀
- v3.5.6-2: 意图规则从 8 条扩到 20 条 (含 sec_fraud/stolen 反诈/盗刷类)
- v3.5.6-3: LLM 兜底前 preprocess_user_input 去除寒暄词

输入: data/evaluation_dataset_v8.0.json (2567 holdout)
输出: data/eval_results_v356.json
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


DATASET_PATH = _ROOT / "data" / "evaluation_dataset_v8.0.json"
OUTPUT_PATH = _ROOT / "data" / "eval_results_v356.json"


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
    print("v3.5.6 真 LLM 评测 - 2567 holdout (修模板 + 规则 + preprocess)")
    print("=" * 80)

    with open(DATASET_PATH, encoding="utf-8") as f:
        dataset = json.load(f)
    samples = dataset["samples"]
    holdout = [s for s in samples if s.get("split") == "holdout"]
    print(f"holdout 样本: {len(holdout)}")
    print()

    pipeline = create_e2e_pipeline(k=3)

    all_results = []
    t0 = time.time()
    total_n = len(holdout)
    for i, sample in enumerate(holdout, 1):
        if i % 500 == 0 or i == 1:
            elapsed = time.time() - t0
            eta = (elapsed / i) * (total_n - i) if i > 0 else 0
            print("  [%d/%d] (%.0f%%)  已用 %.0fs, 预计剩余 %.0fs" % (
                i, total_n, i/total_n*100, elapsed, eta))
        all_results.append(evaluate_sample(pipeline, sample))
    total_elapsed = time.time() - t0
    print("\n  跑完 %d 样本, 总耗时 %.1fs (%.1f 分钟)" % (total_n, total_elapsed, total_elapsed/60))

    overall = aggregate_split(all_results)

    print("\n" + "=" * 80)
    print("v3.5.6 评测结果 (holdout 2567)")
    print("=" * 80)
    for metric in ("intent_accuracy", "p0_recall", "l0_compliance", "rag_hit_rate", "transfer_accuracy"):
        o = overall.get(metric, 0)
        print("%-22s %.2f%%" % (metric, o*100))

    # 与 v3.5.5 对比
    print("\n" + "=" * 80)
    print("v3.5.5 (2567) / v3.5.6 (2567) 对比")
    print("=" * 80)
    print("%-22s %-14s %-14s %-10s" % ("指标", "v3.5.5", "v3.5.6", "Δ"))
    print("-" * 80)
    v355 = {"intent_accuracy": 0.6089, "p0_recall": 0.7601, "l0_compliance": 1.0, "rag_hit_rate": 1.0}
    for k in ("intent_accuracy", "p0_recall", "l0_compliance", "rag_hit_rate"):
        v35_5 = v355[k]
        v35_6 = overall[k]
        delta = (v35_6 - v35_5) * 100
        print("%-22s %6.2f%%       %6.2f%%       %+6.2fpp" % (k, v35_5*100, v35_6*100, delta))

    # 业务组对比
    print("\n业务组对比 (holdout):")
    print("%-12s %-14s %-14s %-10s" % ("业务组", "v3.5.5", "v3.5.6", "Δ"))
    v355_group = {"sales": 0.226, "cons": 0.495, "sec": 0.518, "sys": 0.603, "info": 0.683, "biz": 0.922}
    for g, v35_5 in v355_group.items():
        v35_6 = overall["by_intent_group"].get(g, {}).get("accuracy", 0)
        delta = (v35_6 - v35_5) * 100
        print("%-12s %6.2f%%       %6.2f%%       %+6.2fpp" % (g, v35_5*100, v35_6*100, delta))

    # P0 详细
    print("\nP0 按意图详细 (holdout):")
    for intent, stat in sorted(overall["p0_by_intent"].items()):
        recall = stat.get("recall", 0) * 100
        print("  %-30s: %d/%d = %.1f%%" % (intent, stat["recalled"], stat["total"], recall))

    # 输出
    output = {
        "eval_version": "v3.5.6",
        "eval_date": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "llm": "MiniMax-M2.7 via api.minimaxi.com/v1 (订阅 Key)",
        "dataset_version": "v8.0",
        "patches_applied": "v3.5.6-1: 模板去问候词 + v3.5.6-2: 规则 8->20 + v3.5.6-3: LLM 兜底前 preprocess",
        "summary": {"holdout": overall},
        "total_elapsed_ms": round(total_elapsed * 1000, 1),
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2, default=str)
    print("\n结果保存: %s" % OUTPUT_PATH)


if __name__ == "__main__":
    main()
