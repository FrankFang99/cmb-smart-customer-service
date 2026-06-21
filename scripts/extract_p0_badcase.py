"""
P0 Badcase 抽取 + 混淆矩阵分析
==============================
基于 eval_d_v32_cascade.py 的 cascade 逻辑, 重跑一遍并把每条样本的
(question/expected/actual/source/conf) 存成 JSONL, 然后输出:
  1. P0 group_match=True 但 fine_match=False 的 105 条 (细分 intent 错)
  2. P0 group_match=False 的 69 条 (大类错)
  3. 按业务组拆分的混淆对
  4. 错误归因 (L1 规则错 / L2 BERT 错 / LLM 兜底标记 / label 命名差异)
"""
from __future__ import annotations
import json
import os
import sys
import time
from collections import defaultdict, Counter
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.components.intent_recognizer import IntentRecognizer
from src.nlp.cascade_l2 import get_bert_l2

DATASET_PATH = _ROOT / "data" / "D_eval_set_v3.2.json"
DETAIL_PATH = _ROOT / "data" / "p0_badcase_detail.jsonl"
REPORT_PATH = _ROOT / "data" / "p0_badcase_report.json"

CONFIDENCE_THRESHOLD = 0.85

PREFIX_MAP = {
    "cons": "consult",
    "sales": "mkt",
    "sec": "security",
}


def normalize_d_group(group: str) -> str:
    return PREFIX_MAP.get(group, group)


def cascade_predict(text: str, recognizer: IntentRecognizer, bert_l2) -> dict:
    try:
        from src.eval.badcase_patches_v356 import preprocess_user_input
        clean = preprocess_user_input(text)
    except ImportError:
        clean = text

    rule_result = recognizer.recognize(clean, context=[])
    rule_intent = rule_result.intent_value()
    rule_conf = rule_result.confidence

    if rule_conf >= CONFIDENCE_THRESHOLD:
        return {"intent": rule_intent, "confidence": rule_conf, "source": "L1_rule", "use_llm": False}

    if bert_l2 is not None:
        if not bert_l2.is_available:
            bert_l2.load()
        if bert_l2.is_available:
            bert_pred = bert_l2.predict(clean)
            if bert_pred is not None:
                bert_intent, bert_conf, _ = bert_pred
                if bert_conf >= CONFIDENCE_THRESHOLD:
                    return {"intent": bert_intent, "confidence": bert_conf, "source": "L2_bert", "use_llm": False}

    return {"intent": rule_intent, "confidence": rule_conf, "source": "L3_llm_pending", "use_llm": True}


def evaluate_sample(recognizer, bert_l2, sample) -> dict:
    question = sample["query"]
    expected = sample["intent_top1"]
    priority = sample.get("priority", "P3")
    cascade = cascade_predict(question, recognizer, bert_l2)

    fine_match = cascade["intent"] == expected
    expected_group = expected.split("_")[0]
    actual_group_raw = cascade["intent"].split("_")[0]
    actual_group = normalize_d_group(actual_group_raw)
    group_match = expected_group == actual_group

    return {
        "sample_id": sample["id"],
        "question": question,
        "expected_intent": expected,
        "actual_intent": cascade["intent"],
        "expected_group": expected_group,
        "actual_group": actual_group,
        "priority": priority,
        "cascade_source": cascade["source"],
        "cascade_confidence": round(cascade["confidence"], 4),
        "use_llm_fallback": cascade["use_llm"],
        "fine_match": fine_match,
        "group_match": group_match,
        "tags": sample.get("tags", []),
        "source_kind": sample.get("source", "unknown"),
    }


def attr(r: dict) -> str:
    """错误归因: 4 类"""
    if r["group_match"] and r["fine_match"]:
        return "correct"
    if not r["group_match"]:
        # 大类都错
        if r["cascade_source"] == "L1_rule":
            return "L1_rule_group_miss"
        if r["cascade_source"] == "L2_bert":
            return "L2_bert_group_miss"
        if r["use_llm_fallback"]:
            return "L3_llm_pending_group_miss"
        return "group_miss_other"
    # group 对, fine 错
    if r["cascade_source"] == "L1_rule":
        return "L1_rule_fine_miss"
    if r["cascade_source"] == "L2_bert":
        return "L2_bert_fine_miss"
    if r["use_llm_fallback"]:
        return "L3_llm_pending_fine_miss"
    return "fine_miss_other"


def main():
    print("=" * 70)
    print("P0 Badcase 抽取 + 混淆矩阵分析")
    print("=" * 70)

    with open(DATASET_PATH, encoding="utf-8") as f:
        ds = json.load(f)
    samples = ds["samples"]
    print(f"评测集: {ds['dataset_version']} | 总样本 {len(samples)}")

    recognizer = IntentRecognizer()
    bert_l2 = get_bert_l2()
    bert_l2.load()
    print(f"BERT L2 可用: {bert_l2.is_available} | 路径: {bert_l2.model_path}")

    t0 = time.time()
    details = []
    for i, s in enumerate(samples, 1):
        if i % 200 == 0 or i == 1:
            elapsed = time.time() - t0
            eta = (elapsed / i) * (len(samples) - i) if i > 0 else 0
            print(f"  [{i}/{len(samples)}] ({i/len(samples)*100:.0f}%)  "
                  f"已用 {elapsed:.0f}s, 预计剩余 {eta:.0f}s")
        details.append(evaluate_sample(recognizer, bert_l2, s))
    print(f"\n跑完 {len(samples)} 样本, 耗时 {time.time()-t0:.1f}s")

    # 存 detail
    with open(DETAIL_PATH, "w", encoding="utf-8") as f:
        for d in details:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    print(f"detail: {DETAIL_PATH}")

    # === P0 筛选 ===
    p0 = [d for d in details if d["priority"] == "P0"]
    print(f"\nP0 总数: {len(p0)}")

    p0_group_correct_fine_wrong = [d for d in p0 if d["group_match"] and not d["fine_match"]]
    p0_group_wrong = [d for d in p0 if not d["group_match"]]
    print(f"  group 对 / fine 错 (细分 intent 错): {len(p0_group_correct_fine_wrong)}")
    print(f"  group 错 (大类错):                  {len(p0_group_wrong)}")

    # 错误归因
    attr_counter = Counter()
    for d in p0:
        attr_counter[attr(d)] += 1
    print(f"\nP0 错误归因:")
    for k, v in attr_counter.most_common():
        print(f"  {k}: {v}")

    # === 混淆对 (group_match=False 的大类错) ===
    confusion_group = Counter()
    for d in p0_group_wrong:
        confusion_group[(d["expected_group"], d["actual_group"])] += 1
    print(f"\nP0 group 错 - 混淆对 (expected→actual):")
    for (exp, act), n in confusion_group.most_common(15):
        print(f"  {exp:10s} → {act:10s}  {n} 条")

    # === 混淆对 (group 对 / fine 错) - 细分 intent 错 ===
    confusion_fine = Counter()
    for d in p0_group_correct_fine_wrong:
        # 取前 4 段: sys_service_001 这种
        # 用 expected_group 与 actual_group 都相同, 但具体 intent 错
        confusion_fine[(d["expected_intent"], d["actual_intent"])] += 1
    print(f"\nP0 fine 错 - Top 20 混淆 intent 对 (expected→actual):")
    for (exp, act), n in confusion_fine.most_common(20):
        print(f"  {exp:30s} → {act:30s}  {n} 条")

    # === 按业务组拆 fine 错 ===
    by_group_fine_miss = defaultdict(list)
    for d in p0_group_correct_fine_wrong:
        by_group_fine_miss[d["expected_group"]].append(d)
    print(f"\nP0 fine 错 - 按业务组拆分:")
    for g, lst in sorted(by_group_fine_miss.items(), key=lambda x: -len(x[1])):
        print(f"  {g:10s} {len(lst):3d} 条")

    # === 按业务组拆 group 错 ===
    by_group_miss = defaultdict(list)
    for d in p0_group_wrong:
        by_group_miss[d["expected_group"]].append(d)
    print(f"\nP0 group 错 - 按业务组拆分:")
    for g, lst in sorted(by_group_miss.items(), key=lambda x: -len(x[1])):
        print(f"  {g:10s} {len(lst):3d} 条")

    # === Cascade 源在 P0 fine 错中的分布 ===
    src_fine_miss = Counter()
    for d in p0_group_correct_fine_wrong:
        src_fine_miss[d["cascade_source"]] += 1
    print(f"\nP0 fine 错 - cascade source 分布:")
    for s, n in src_fine_miss.most_common():
        print(f"  {s}: {n}")

    # === 抽 5 个 badcase 样本 (按 group) ===
    print(f"\n=== 抽 5 个不同业务组的 fine 错样本 (作为示例) ===")
    seen = set()
    for d in p0_group_correct_fine_wrong:
        if d["expected_group"] not in seen:
            seen.add(d["expected_group"])
            print(f"  [{d['expected_group']}] Q: {d['question']}")
            print(f"    expected: {d['expected_intent']} | actual: {d['actual_intent']}")
            print(f"    source={d['cascade_source']} conf={d['cascade_confidence']}")
            if len(seen) >= 5:
                break

    # === 报告 JSON ===
    report = {
        "dataset_version": ds["dataset_version"],
        "total_samples": len(samples),
        "p0_total": len(p0),
        "p0_group_correct_fine_wrong": len(p0_group_correct_fine_wrong),
        "p0_group_wrong": len(p0_group_wrong),
        "attr_distribution": dict(attr_counter),
        "confusion_group_top20": [
            {"expected": k[0], "actual": k[1], "count": v}
            for k, v in confusion_group.most_common(20)
        ],
        "confusion_fine_top20": [
            {"expected": k[0], "actual": k[1], "count": v}
            for k, v in confusion_fine.most_common(20)
        ],
        "fine_miss_by_group": {g: len(lst) for g, lst in by_group_fine_miss.items()},
        "group_miss_by_group": {g: len(lst) for g, lst in by_group_miss.items()},
        "fine_miss_source_distribution": dict(src_fine_miss),
    }
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n报告: {REPORT_PATH}")


if __name__ == "__main__":
    main()
