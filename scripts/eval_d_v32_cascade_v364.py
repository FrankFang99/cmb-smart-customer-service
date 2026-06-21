"""
Cascade L2 BERT 评测 - D_eval_set_v3.2 (1500 条黄金评测集)
=========================================================
承接 v3.6.0 Cascade runner, 适配 D 评测集 v3.2 schema:

- L1 规则 (IntentRecognizer) → 置信度 >= 0.85 → 返回
                              ↓ < 0.85
- L2 BERT (M3 微调) → 置信度 >= 0.85 → 返回
                     ↓ < 0.85
- L3 LLM 兜底 (标记 use_llm=True)

新增 P0 红线召回率 (v3.6.0 runner 没单独算这个).
新增 priority 分桶准确率 (P0/P1/P2/P3).

对比基线:
- v3.5.5: 60.89%
- v3.5.6: 68.25%
- M4 (L1 only): 67.04%
- v3.6.0 on v8.0 holdout: ?
"""
from __future__ import annotations
import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

# UTF-8 (Windows 中文路径)
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.components.intent_recognizer import IntentRecognizer
from src.nlp.cascade_l2 import get_bert_l2

DATASET_PATH = _ROOT / "data" / "D_eval_set_v3.2.json"
OUTPUT_PATH = _ROOT / "data" / "eval_results_d_v32_cascade_v364.json"

CONFIDENCE_THRESHOLD = 0.85

# IR 前缀 → D 前缀 映射（修复 IR vs D label 命名差异）
# 根因: A_standard v3.2 重构成 86 个细类 + 7 个业务组 (consult/mkt/safety)
#        但 IntentRecognizer 还停留在 v3.5.x 的 99 个旧 label (cons/sales/sec)
PREFIX_MAP = {
    "cons": "consult",
    "sales": "mkt",
    "sec": "security",  # sec 全部归 security; safety 在 IR 暂无对应, 视作 LLM 兜底或 L3 补
}


def normalize_d_group(group: str) -> str:
    return PREFIX_MAP.get(group, group)


def cascade_predict(text: str, recognizer: IntentRecognizer, bert_l2) -> dict:
    """L1 规则 -> L2 BERT -> L3 LLM 兜底"""
    # preprocess (v3.5.6 修寒暄)
    try:
        from src.eval.badcase_patches_v356 import preprocess_user_input
        clean = preprocess_user_input(text)
    except ImportError:
        clean = text

    # L1 规则
    rule_result = recognizer.recognize(clean, context=[])
    rule_intent = rule_result.intent_value()
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


def evaluate_sample(recognizer, bert_l2, sample) -> dict:
    question = sample["query"]
    expected = sample["intent_top1"]
    priority = sample.get("priority", "P3")
    t0 = time.time()
    cascade = cascade_predict(question, recognizer, bert_l2)
    elapsed = (time.time() - t0) * 1000

    # 细类严格匹配（受 label 命名差异影响, 仅做参考）
    fine_match = cascade["intent"] == expected
    # 业务组层级匹配（PM 视角: 不在意叫 tran 还是 transfer, 在意分到 transfer 类）
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
        "cascade_confidence": cascade["confidence"],
        "use_llm_fallback": cascade["use_llm"],
        "fine_match": fine_match,
        "group_match": group_match,
        "tags": sample.get("tags", []),
        "source_kind": sample.get("source", "unknown"),
        "elapsed_ms": round(elapsed, 2),
    }


def main():
    print("=" * 70)
    print("Cascade L2 BERT 评测 v3.6.4 - D_eval_set_v3.2 (1500 条黄金评测集)")
    print("v3.6.4 patches: 口语化转人工 + 假冒公安 + 短 query patterns")
    print("=" * 70)

    with open(DATASET_PATH, encoding="utf-8") as f:
        ds = json.load(f)
    samples = ds["samples"]
    print(f"评测集: {ds['dataset_version']} | 总样本 {len(samples)}")
    print(f"P0: {ds.get('p0_count', '?')} | P1: {ds.get('p1_count', '?')} | "
          f"P2: {ds.get('p2_count', '?')} | P3: {ds.get('p3_count', '?')}")

    recognizer = IntentRecognizer()
    bert_l2 = get_bert_l2()
    bert_l2.load()
    print(f"BERT L2 可用: {bert_l2.is_available} | 路径: {bert_l2.model_path}")

    results = []
    t0 = time.time()
    for i, s in enumerate(samples, 1):
        if i % 200 == 0 or i == 1:
            elapsed = time.time() - t0
            eta = (elapsed / i) * (len(samples) - i) if i > 0 else 0
            print(f"  [{i}/{len(samples)}] ({i/len(samples)*100:.0f}%)  已用 {elapsed:.0f}s, 预计剩余 {eta:.0f}s")
        results.append(evaluate_sample(recognizer, bert_l2, s))
    total = time.time() - t0
    print(f"\n跑完 {len(samples)} 样本, 总耗时 {total:.1f}s ({total/60:.1f} 分钟)")

    # === 全局指标 ===
    fine_correct = sum(1 for r in results if r["fine_match"])
    fine_acc = fine_correct / len(results)
    group_correct = sum(1 for r in results if r["group_match"])
    group_acc = group_correct / len(results)
    acc = group_acc  # PM 主指标用 group-level
    correct = group_correct
    llm_fallback_pct = sum(1 for r in results if r["use_llm_fallback"]) / len(results) * 100

    # === P0 红线召回率（银行业核心 KPI）===
    p0_results = [r for r in results if r["priority"] == "P0"]
    p0_recall = sum(1 for r in p0_results if r["group_match"]) / len(p0_results) if p0_results else 0
    p0_fine_recall = sum(1 for r in p0_results if r["fine_match"]) / len(p0_results) if p0_results else 0

    # === P0 业务口径 (v3.6.3 报告 §2.1 诚实修正) ===
    # 业务口径: actual_intent 落在 P0 intent 集内才算命中
    P0_INTENT_SET = {
        "sys_service_route_human", "sys_service_complaint",
        "safety_card_loss", "safety_card_freeze",
        "security_fraud_report", "security_fraud_recognize",
        "security_aml_cross_border", "security_aml_large_transfer",
        "security_promise_yield",
        "security_suitability_mismatch", "security_suitability_unrated",
        "biz_optout_outbound",
    }
    p0_recall_business = sum(
        1 for r in p0_results
        if r["actual_intent"] in P0_INTENT_SET or r["fine_match"]
    ) / len(p0_results) if p0_results else 0

    # === P0 业务等价口径 (含 safety_card_loss ↔ security_fraud_report 双意图互抢) ===
    P0_BUSINESS_EQUIVALENT = P0_INTENT_SET | {
        # 双意图设计: 业务上都触发转人工
        "sec_fraud_report",  # IR 老 label, 业务上等价于 security_fraud_report
        "sec_stolen_card",   # IR 老 label, 业务上等价于 safety_card_loss
    }
    p0_recall_business_eq = sum(
        1 for r in p0_results
        if r["actual_intent"] in P0_BUSINESS_EQUIVALENT or r["fine_match"]
    ) / len(p0_results) if p0_results else 0

    # === 优先级分桶准确率 ===
    by_priority = defaultdict(lambda: {"total": 0, "group_correct": 0, "fine_correct": 0, "llm": 0})
    for r in results:
        p = r["priority"]
        by_priority[p]["total"] += 1
        if r["group_match"]:
            by_priority[p]["group_correct"] += 1
        if r["fine_match"]:
            by_priority[p]["fine_correct"] += 1
        if r["use_llm_fallback"]:
            by_priority[p]["llm"] += 1
    for p, s in by_priority.items():
        s["group_accuracy"] = round(s["group_correct"] / s["total"], 4) if s["total"] else 0
        s["fine_accuracy"] = round(s["fine_correct"] / s["total"], 4) if s["total"] else 0
        s["llm_pct"] = round(s["llm"] / s["total"] * 100, 2) if s["total"] else 0

    # === Cascade 分流分布 ===
    source_count = defaultdict(int)
    for r in results:
        source_count[r["cascade_source"]] += 1

    # === 业务组准确率 (按 intent 前缀) ===
    by_group = defaultdict(lambda: {"total": 0, "group_correct": 0, "fine_correct": 0})
    for r in results:
        g = r["expected_intent"].split("_")[0]
        by_group[g]["total"] += 1
        if r["group_match"]:
            by_group[g]["group_correct"] += 1
        if r["fine_match"]:
            by_group[g]["fine_correct"] += 1
    for g, s in by_group.items():
        s["group_accuracy"] = round(s["group_correct"] / s["total"], 4) if s["total"] else 0
        s["fine_accuracy"] = round(s["fine_correct"] / s["total"], 4) if s["total"] else 0

    # === 来源分桶准确率 ===
    by_source = defaultdict(lambda: {"total": 0, "group_correct": 0})
    for r in results:
        by_source[r["source_kind"]]["total"] += 1
        if r["group_match"]:
            by_source[r["source_kind"]]["group_correct"] += 1
    for k, s in by_source.items():
        s["group_accuracy"] = round(s["group_correct"] / s["total"], 4) if s["total"] else 0

    # === 输出 ===
    print(f"\n{'='*70}")
    print(f"=== Cascade 实测 KPI (D_eval_set_v3.2) ===")
    print(f"{'='*70}")
    print(f"\n【核心 KPI】")
    print(f"  整体意图准确率 (业务组级, 含前缀映射): {acc*100:.2f}% ({correct}/{len(results)})")
    print(f"  细类匹配 (label 名同):                  {fine_acc*100:.2f}% ({fine_correct}/{len(results)})  [参考, 受命名差异影响]")
    print(f"  P0 红线召回 (组级):                     {p0_recall*100:.2f}% "
          f"({sum(1 for r in p0_results if r['group_match'])}/{len(p0_results)})  ★ 银行业核心")
    print(f"  P0 业务口径 (should_transfer):          {p0_recall_business*100:.2f}% "
          f"({sum(1 for r in p0_results if r['actual_intent'] in P0_INTENT_SET or r['fine_match'])}/{len(p0_results)})  [v3.6.3 §2.1]")
    print(f"  P0 业务等价口径 (含 sec_fraud 互抢):    {p0_recall_business_eq*100:.2f}%  [业务真正转人工]")
    print(f"  P0 细类召回 (label 名同):               {p0_fine_recall*100:.2f}%  [参考]")
    print(f"  LLM 兜底占比:                           {llm_fallback_pct:.2f}%  ★ 成本/数据安全指标")

    print(f"\n【优先级分桶 (组级)】")
    for p in ["P0", "P1", "P2", "P3"]:
        if p in by_priority:
            s = by_priority[p]
            print(f"  {p}: 准确率 {s['group_accuracy']*100:6.2f}% ({s['group_correct']:4d}/{s['total']:4d})  "
                  f"LLM 兜底 {s['llm_pct']:5.2f}%")

    print(f"\n【Cascade 分流】")
    for s, c in sorted(source_count.items(), key=lambda x: -x[1]):
        print(f"  {s:18s} {c:4d} ({c/len(results)*100:5.1f}%)")

    print(f"\n【业务组准确率 (组级, 含前缀映射)】")
    for g, s in sorted(by_group.items()):
        print(f"  {g:10s} {s['group_accuracy']*100:6.2f}% ({s['group_correct']:4d}/{s['total']:4d})")

    print(f"\n【评测集来源分桶 (组级)】")
    for k, s in sorted(by_source.items()):
        print(f"  {k:18s} {s['group_accuracy']*100:6.2f}% ({s['group_correct']:4d}/{s['total']:4d})")

    # 对比历史版本
    print(f"\n{'='*70}")
    print(f"=== 历史版本对比 ===")
    v355 = 60.89
    v356 = 68.25
    m4 = 67.04
    v360_before_fix = 35.27  # 修复前: safety 组 0%, P0 召回 26%
    v360_p0_before = 26.00
    v361_p0 = 66.75  # v3.6.1 P0 红线召回 (评测口径)
    v362_p0 = 79.87  # v3.6.2 PM 重审后
    v363_p0 = 89.06  # v3.6.3 三类 P0 patterns 扩展
    v363_p0_business = 87.80  # v3.6.3 业务口径
    print(f"  v3.5.5 (no L2):       60.89%  | v3.5.6 (no L2): 68.25%  | M4 (L1 only): 67.04%")
    print(f"  v3.6.0 (修复前):       {v360_before_fix:.2f}% (P0 召回 {v360_p0_before:.2f}%)  [safety 组 0% 拖累]")
    print(f"  v3.6.1 (修复后):       P0 召回 {v361_p0:.2f}%  [v3.6.1 P0 红线补丁, 11 类 D v3.2 intent]")
    print(f"  v3.6.2 (PM 重审):      P0 召回 {v362_p0:.2f}%  [21 P0 → 12 P0, 业务口径修正]")
    print(f"  v3.6.3 (三类扩展):     P0 召回 {v363_p0:.2f}% / 业务 {v363_p0_business:.2f}%  [safety/complaint/optout]")
    print(f"  v3.6.4 (本次):         P0 召回 {p0_recall*100:.2f}% / 业务 {p0_recall_business*100:.2f}%  [口语化转人工/假冒公安/短 query]")
    print(f"  P0 累计提升:           +{p0_recall*100-v360_p0_before:.2f}pp (评测口径)")
    print(f"  注: v3.6.4 给 IR 加 6 类 D v3.2 P0 intent patterns 扩展 (口语化/假冒公安/短 query),")
    print(f"      修复 v3.6.3 报告 §5 的 127 条 P0 业务 miss 中 64 条.")
    print(f"{'='*70}")

    # 保存
    output = {
        "eval_version": "v3.6.4-cascade-l2-on-D-v3.2",
        "eval_date": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "dataset_version": ds["dataset_version"],
        "dataset_total": len(samples),
        "bert_l2_available": bert_l2.is_available,
        "bert_l2_path": bert_l2.model_path,
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "prefix_map": PREFIX_MAP,
        "note": "评测指标用业务组 (prefix) 匹配, 已加 IR→D 前缀映射 (cons→consult, sales→mkt, sec→security)",
        "core_kpi": {
            "intent_accuracy_group": round(group_acc, 4),
            "intent_accuracy_fine": round(fine_acc, 4),
            "p0_recall_group": round(p0_recall, 4),
            "p0_recall_business": round(p0_recall_business, 4),
            "p0_recall_business_equivalent": round(p0_recall_business_eq, 4),
            "p0_recall_fine": round(p0_fine_recall, 4),
            "llm_fallback_pct": round(llm_fallback_pct, 2),
        },
        "by_priority": {p: dict(s) for p, s in by_priority.items()},
        "by_source_kind": {k: dict(s) for k, s in by_source.items()},
        "by_intent_group": dict(by_group),
        "cascade_source_count": dict(source_count),
        "comparison": {
            "v355": v355,
            "v356": v356,
            "m4": m4,
            "v360_d_v32_group": round(group_acc * 100, 2),
            "v361_p0_recall": v361_p0,
            "v362_p0_recall": v362_p0,
            "v363_p0_recall": v363_p0,
            "v363_p0_business_recall": v363_p0_business,
            "v364_p0_recall": round(p0_recall * 100, 2),
            "v364_p0_business_recall": round(p0_recall_business * 100, 2),
            "v364_p0_business_equivalent_recall": round(p0_recall_business_eq * 100, 2),
        },
        "total_elapsed_s": round(total, 1),
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n结果已存: {OUTPUT_PATH}")
    return output


if __name__ == "__main__":
    main()
