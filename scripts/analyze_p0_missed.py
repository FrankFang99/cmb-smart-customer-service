"""
提取 1500 条全量里的 P0 漏检 case + 完整链路分析
"""
import sys
import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from src.observability.trace_query import TraceQuery
from src.observability.badcase_replayer import BadCaseReplayer


def main():
    q = TraceQuery()

    # 1. 找 P0 但 final_action != transfer_human 的 trace
    all_p0 = q.list_traces(limit=100000, priority="P0")
    missed = [t for t in all_p0 if not t["p0_triggered"]]
    print(f"P0 总数: {len(all_p0)}")
    print(f"P0 漏检: {len(missed)} 条")
    print(f"P0 召回: {(len(all_p0)-len(missed))/len(all_p0):.1%}")

    print(f"\n{'='*70}")
    print(f"P0 漏检 Case 完整链路分析")
    print(f"{'='*70}")

    replayer = BadCaseReplayer()
    missed_reports = []

    for i, t in enumerate(missed, 1):
        report = replayer.replay(t["trace_id"], auto_detect_bad_case=False)
        missed_reports.append(report)

        print(f"\n--- Case {i}/{len(missed)} ---")
        print(f"Trace ID: {report.trace_id}")
        print(f"用户输入: {report.user_input}")
        print(f"Priority: {report.priority}")
        print(f"Expected: {report.expected_action}")
        print(f"Final: action={report.final_action}, intent={report.final_intent}")
        print(f"P0 触发: {report.p0_triggered}  ⚠️ 漏检")

        # 时间线
        print(f"\n链路 ({len(report.timeline)} spans):")
        for span in report.timeline:
            indent = "  " if not span["name"].startswith("L") else ""
            print(f"  {indent}{span['name']:25s} [{span.get('layer', '?'):6s}] "
                  f"{span.get('elapsed_ms', 0):6.1f}ms {span['status']}")

        # 关键属性
        print(f"\n关键属性:")
        for step in report.cascade_path:
            layer = step.get("layer", "?")
            extras = " ".join(f"{k}={v}" for k, v in step.items()
                              if k not in ("layer", "span_name"))
            print(f"  {layer}: {extras}")

        # RAG 命中
        if report.rag_hits:
            print(f"\nRAG 检索命中 ({len(report.rag_hits)}):")
            for h in report.rag_hits[:3]:
                print(f"  - {h.get('doc_id', '?')}: {h.get('title', '?')} (score={h.get('score', '?')})")

    # 2. 漏检原因分类 (PM 视角)
    print(f"\n{'='*70}")
    print(f"PM 视角: 7 条 P0 漏检原因分析")
    print(f"{'='*70}")

    reasons = {
        "intent_outside_l0_dict": [],  # 关键词没在 L0 词典
        "intent_outside_l1_p0_set": [],  # L1 也没识别为 P0
        "l3_fallback_missed": [],  # L3 LLM 没识破
    }

    for r in missed_reports:
        # 从 cascade_path 找根因
        layers = [s.get("layer") for s in r.cascade_path]
        l0_hit = any("l0_triggered" in str(s) and "True" in str(s) for s in r.cascade_path if s.get("layer") == "L0")
        l1_p0 = any(s.get("is_p0") == True for s in r.cascade_path if s.get("layer") == "L1")

        if not l0_hit and not l1_p0:
            reasons["intent_outside_l0_dict"].append(r)
        elif l1_p0:
            reasons["intent_outside_l1_p0_set"].append(r)
        else:
            reasons["l3_fallback_missed"].append(r)

    for reason_key, cases in reasons.items():
        if not cases:
            continue
        print(f"\n[{reason_key}] - {len(cases)} 条")
        for c in cases:
            print(f"  - {c.user_input[:60]}")

    # 3. 建议的 patch 方向
    print(f"\n{'='*70}")
    print(f"建议的 Patch 方向 (PM 决策)")
    print(f"{'='*70}")

    # 统计关键词 (用于 patch 词典扩展)
    from collections import Counter
    keyword_counter = Counter()
    for r in missed_reports:
        for char in r.user_input:
            if '\u4e00' <= char <= '\u9fff' and len(char) == 1:  # 中文
                keyword_counter[char] += 1

    # 找高频词 (出现在漏检 query 中的)
    print(f"\n漏检 query 的高频字 (扩展 L0 词典参考):")
    for char, cnt in keyword_counter.most_common(30):
        if cnt >= 2:
            print(f"  '{char}': {cnt} 次")

    # 保存分析报告
    output = {
        "p0_total": len(all_p0),
        "p0_missed": len(missed),
        "p0_recall_rate": (len(all_p0)-len(missed))/len(all_p0),
        "missed_cases": [
            {
                "trace_id": r.trace_id,
                "user_input": r.user_input,
                "expected_action": r.expected_action,
                "final_action": r.final_action,
                "final_intent": r.final_intent,
                "cascade_path": r.cascade_path,
                "rag_hits": r.rag_hits,
                "timeline_summary": [{"name": t["name"], "layer": t.get("layer"), "elapsed_ms": t.get("elapsed_ms"), "status": t["status"]} for t in r.timeline],
            }
            for r in missed_reports
        ],
        "reason_breakdown": {k: len(v) for k, v in reasons.items()},
        "high_freq_keywords": [{"char": c, "count": n} for c, n in keyword_counter.most_common(30) if n >= 2],
    }
    out_path = _ROOT / "data" / "p0_missed_analysis.json"
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n分析报告: {out_path}")


if __name__ == "__main__":
    main()