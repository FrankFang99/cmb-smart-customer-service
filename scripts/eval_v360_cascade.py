"""
v3.6.0 Cascade L2 BERT 评测 - 2567 holdout
===========================================
新流程:
- L1 规则 (IntentRecognizer) → 置信度 >= 0.85 → 返回
                              ↓ < 0.85
- L2 BERT (M3 微调) → 置信度 >= 0.85 → 返回
                     ↓ < 0.85
- L3 LLM 兜底 (v3.5.6 preprocess + LLM)

对比:
- v3.5.5 (no L2): 60.89% 意图
- v3.5.6 (no L2): 68.25% 意图
- v3.6.0 (with L2): 预期 80%+
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

os_env_setup = {**__import__('os').environ, "PYTHONIOENCODING": "utf-8"}
__import__('os').environ.update(os_env_setup)

import os
from src.components.intent_recognizer import IntentRecognizer
from src.nlp.cascade_l2 import get_bert_l2


DATASET_PATH = _ROOT / "data" / "evaluation_dataset_v8.0.json"
OUTPUT_PATH = _ROOT / "data" / "eval_results_v360.json"

CONFIDENCE_THRESHOLD = 0.85  # L1/L2 门限


def cascade_predict(text: str, recognizer: IntentRecognizer, bert_l2) -> dict:
    """
    L1 规则 -> L2 BERT -> L3 LLM 兜底

    Returns:
        {intent, confidence, source, use_llm_fallback}
    """
    # preprocess 去除寒暄词 (v3.5.6 修复)
    try:
        from src.eval.badcase_patches_v356 import preprocess_user_input
        clean = preprocess_user_input(text)
    except ImportError:
        clean = text

    # L1 规则
    rule_result = recognizer.recognize(clean, context=[])
    rule_intent = rule_result.intent.value
    rule_conf = rule_result.confidence

    if rule_conf >= CONFIDENCE_THRESHOLD:
        return {"intent": rule_intent, "confidence": rule_conf, "source": "L1_rule", "use_llm": False}

    # L2 BERT
    if bert_l2 is not None:
        if not bert_l2.is_available:
            bert_l2.load()
        if bert_l2.is_available:
            bert_pred = bert_l2.predict(clean)
            if bert_pred is not None:
                bert_intent, bert_conf, _ = bert_pred
                if bert_conf >= CONFIDENCE_THRESHOLD:
                    return {"intent": bert_intent, "confidence": bert_conf, "source": "L2_bert", "use_llm": False}

    # L3 LLM 兜底
    return {"intent": rule_intent, "confidence": rule_conf, "source": "L3_llm_pending", "use_llm": True}


def evaluate_sample(recognizer, bert_l2, sample, llm_client=None) -> dict:
    question = sample["question"]
    expected = sample["intent"]
    t0 = time.time()
    cascade = cascade_predict(question, recognizer, bert_l2)

    # L3 兜底 (本期为简单模拟, 实际调 LLM 会在 L3 路径下走; 这里用 cascade 自身 result)
    final_intent = cascade["intent"]
    if cascade["use_llm"] and llm_client is not None:
        # 实际场景会调 LLM, 评测时为节省 token, 沿用 L1 规则
        pass

    elapsed = (time.time() - t0) * 1000
    return {
        "sample_id": sample["id"],
        "question": question,
        "expected_intent": expected,
        "actual_intent": final_intent,
        "cascade_source": cascade["source"],
        "cascade_confidence": cascade["confidence"],
        "use_llm_fallback": cascade["use_llm"],
        "intent_match": final_intent == expected,
        "elapsed_ms": round(elapsed, 2),
    }


def main():
    print("=" * 70)
    print("v3.6.0 Cascade L2 BERT 评测 - 2567 holdout")
    print("=" * 70)

    with open(DATASET_PATH, encoding="utf-8") as f:
        ds = json.load(f)
    holdout = [s for s in ds["samples"] if s.get("split") == "holdout"]
    print(f"holdout: {len(holdout)}")

    recognizer = IntentRecognizer()
    bert_l2 = get_bert_l2()
    bert_l2.load()  # 尝试加载 (M3 训完才有)
    print(f"BERT L2 可用: {bert_l2.is_available}")

    results = []
    t0 = time.time()
    for i, s in enumerate(holdout, 1):
        if i % 500 == 0 or i == 1:
            elapsed = time.time() - t0
            eta = (elapsed / i) * (len(holdout) - i) if i > 0 else 0
            print(f"  [{i}/{len(holdout)}] ({i/len(holdout)*100:.0f}%)  已用 {elapsed:.0f}s, 预计剩余 {eta:.0f}s")
        results.append(evaluate_sample(recognizer, bert_l2, s))
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

    source_count = defaultdict(int)
    for r in results:
        source_count[r.get("cascade_source", "unknown")] += 1

    llm_fallback_pct = sum(1 for r in results if r.get("use_llm_fallback")) / len(results) * 100

    print(f"\n=== v3.6.0 Cascade L2 结果 ===")
    print(f"意图准确率: {acc*100:.2f}% ({correct}/{len(results)})")
    print(f"LLM 兜底占比: {llm_fallback_pct:.2f}% (低置信 fallback)")
    print(f"\nCascade 分流:")
    for s, c in sorted(source_count.items(), key=lambda x: -x[1]):
        print(f"  {s}: {c} ({c/len(results)*100:.1f}%)")
    print(f"\n业务组准确率:")
    for g, s in sorted(by_group.items()):
        print(f"  {g:10s} {s['accuracy']*100:6.2f}% ({s['correct']}/{s['total']})")

    # 对比 v3.5.5/v3.5.6/M4
    print(f"\n=== 对比 ===")
    v355 = 60.89
    v356 = 68.25
    m4 = 67.04
    print(f"  v3.5.5: 60.89%  | v3.5.6: 68.25%  | M4 (L1 only): 67.04%  | v3.6.0: {acc*100:.2f}%")
    print(f"  v3.6.0 vs v3.5.6: {(acc*100 - v356):+.2f}pp")

    output = {
        "eval_version": "v3.6.0-cascade-l2",
        "eval_date": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "bert_l2_available": bert_l2.is_available,
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "summary": {
            "holdout_acc": acc,
            "llm_fallback_pct": llm_fallback_pct,
            "by_intent_group": dict(by_group),
            "cascade_source_count": dict(source_count),
        },
        "total_elapsed_s": round(total, 1),
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n结果: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
