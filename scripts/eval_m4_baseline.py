"""
M4 基线: 只用 L1 规则 (IntentRecognizer) 不调 BERT/LLM
======================================================
- 输入: data/evaluation_dataset_v8.0.json (2567 holdout)
- 输出: data/eval_results_m4_baseline.json
- 用途: 模型选型对比表 - 下限基线
"""
from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.components.intent_recognizer import IntentRecognizer


DATASET_PATH = _ROOT / "data" / "evaluation_dataset_v8.0.json"
OUTPUT_PATH = _ROOT / "data" / "eval_results_m4_baseline.json"


def evaluate_sample(recognizer: IntentRecognizer, sample: dict) -> dict:
    question = sample["question"]
    expected = sample["intent"]
    t0 = time.time()
    try:
        # 用 preprocess_user_input 仿 v3.5.6 清理
        from src.eval.badcase_patches_v356 import preprocess_user_input
        clean = preprocess_user_input(question)
        result = recognizer.recognize(clean)
        actual = result.intent
        conf = getattr(result, "confidence", 1.0)
    except Exception as e:
        return {
            "sample_id": sample["id"],
            "question": question,
            "expected_intent": expected,
            "error": str(e),
            "intent_match": False,
            "elapsed_ms": 0,
        }
    elapsed = (time.time() - t0) * 1000
    return {
        "sample_id": sample["id"],
        "question": question,
        "expected_intent": expected,
        "actual_intent": actual,
        "confidence": conf,
        "intent_match": actual == expected,
        "elapsed_ms": round(elapsed, 2),
    }


def main():
    print("=" * 70)
    print("M4 基线评测: L1 规则 only (no BERT, no LLM)")
    print("=" * 70)

    with open(DATASET_PATH, encoding="utf-8") as f:
        ds = json.load(f)
    holdout = [s for s in ds["samples"] if s.get("split") == "holdout"]
    print(f"holdout 样本: {len(holdout)}")

    recognizer = IntentRecognizer()
    results = []
    t0 = time.time()
    for i, s in enumerate(holdout, 1):
        if i % 500 == 0 or i == 1:
            elapsed = time.time() - t0
            eta = (elapsed / i) * (len(holdout) - i)
            print(f"  [{i}/{len(holdout)}] ({i/len(holdout)*100:.0f}%)  已用 {elapsed:.0f}s, 预计剩余 {eta:.0f}s")
        results.append(evaluate_sample(recognizer, s))
    total = time.time() - t0
    print(f"\n跑完 {len(holdout)} 样本, 总耗时 {total:.1f}s ({total/60:.1f} 分钟)")

    # 统计
    correct = sum(1 for r in results if r.get("intent_match"))
    acc = correct / len(results)

    by_group = defaultdict(lambda: {"total": 0, "correct": 0})
    for r in results:
        g = r["expected_intent"].split("_")[0]
        by_group[g]["total"] += 1
        if r.get("intent_match"):
            by_group[g]["correct"] += 1
    for g in by_group:
        by_group[g]["accuracy"] = round(by_group[g]["correct"] / by_group[g]["total"], 4)

    print(f"\n=== M4 基线结果 ===")
    print(f"意图准确率: {acc*100:.2f}% ({correct}/{len(results)})")
    print(f"平均耗时: {sum(r.get('elapsed_ms', 0) for r in results)/len(results):.2f}ms")
    print(f"\n业务组准确率:")
    for g, s in sorted(by_group.items()):
        print(f"  {g:10s} {s['accuracy']*100:6.2f}% ({s['correct']}/{s['total']})")

    output = {
        "eval_version": "M4-baseline-L1-only",
        "eval_date": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "model": "M4: L1 rule-only (IntentRecognizer, no BERT, no LLM)",
        "summary": {
            "holdout_acc": acc,
            "by_intent_group": dict(by_group),
        },
        "total_elapsed_s": round(total, 1),
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n结果: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
