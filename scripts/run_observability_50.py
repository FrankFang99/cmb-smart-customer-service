"""
50 条分层采样可观测评测 — 完整端到端验证
"""
import sys
import json
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from src.agent.cascade_observable_v39 import ObservableCascadeV39
from src.observability.trace_query import TraceQuery
from src.observability.badcase_replayer import BadCaseReplayer

print("=" * 70)
print("可观测平台 v3.9.0 — 50 条分层采样完整验证")
print("=" * 70)

# 加载测试集
eval_path = _ROOT / "data" / "D_eval_set_v3.2.json"
with open(eval_path, "r", encoding="utf-8") as f:
    eval_data = json.load(f)
eval_items = eval_data.get("samples", []) if isinstance(eval_data, dict) else eval_data

# 分层采样 P0/P1/P2/P3 各 12-13 条
p0 = [s for s in eval_items if s.get("priority") == "P0"][:13]
p1 = [s for s in eval_items if s.get("priority") == "P1"][:13]
p2 = [s for s in eval_items if s.get("priority") == "P2"][:12]
p3 = [s for s in eval_items if s.get("priority") == "P3"][:12]
samples = p0 + p1 + p2 + p3

print(f"\n样本: P0:{len(p0)} P1:{len(p1)} P2:{len(p2)} P3:{len(p3)} = {len(samples)} 条")

# 开 LLM 跑真实链路 (这才是真跑)
import os
os.environ.setdefault("MINIMAX_MODEL", "MiniMax-M2.7")

cascade = ObservableCascadeV39(enable_llm=True, confidence_threshold=0.85)
results = []

print(f"\n开始跑 Cascade (LLM={os.environ.get('MINIMAX_MODEL')})...\n")
t0 = time.time()
for i, item in enumerate(samples):
    if isinstance(item, dict):
        query = item.get("query") or item.get("text") or str(item)
        expected = item.get("expected_action") or item.get("label") or "unknown"
        priority = item.get("priority", "?")
        intent_top1 = item.get("intent_top1", "?")
    else:
        query = str(item)
        expected = "unknown"
        priority = "?"
        intent_top1 = "?"

    result = cascade.handle(
        query, priority=priority,
        expected_action=expected, intent_top1=intent_top1,
    )
    elapsed_so_far = time.time() - t0
    icon = "🔴" if result["p0_triggered"] else ("⚠️" if result["final_action"] == "fallback_to_human" else "✅")
    print(
        f"[{i+1:2d}/{len(samples)}] [{priority}] {intent_top1:30s} "
        f"→ {result['final_action']:20s} {icon} "
        f"spans={result.get('span_count', 0):2d} {result['elapsed_ms']:6.1f}ms "
        f"| 累计 {elapsed_so_far:.1f}s"
    )
    results.append({
        "trace_id": result["trace_id"],
        "priority": priority,
        "expected_action": expected,
        "final_action": result["final_action"],
        "p0_triggered": result["p0_triggered"],
        "elapsed_ms": result["elapsed_ms"],
        "span_count": result.get("span_count", 0),
    })

# 统计
q = TraceQuery()
total_elapsed = time.time() - t0
print(f"\n{'='*70}")
print(f"总耗时: {total_elapsed:.1f}s ({total_elapsed/len(samples):.1f}s/条)")
print(f"\n[各层调用统计]")
for layer, s in q.layer_stats().items():
    print(f"  {layer}: {s['count']}次, 平均{s['avg_elapsed_ms']:.1f}ms, 错误{s['error_count']}")

print(f"\n[P0 召回]")
for pri, s in q.p0_recall().items():
    print(f"  {pri}: {s['p0_caught']}/{s['total']} = {s['recall_rate']:.1%}")

bad_cases = q.list_traces(is_bad_case=True, limit=20)
print(f"\n[自动检测 Bad Case]: {len(bad_cases)} 条")
for bc in bad_cases[:5]:
    print(f"  - {bc['trace_id']}: {bc.get('bad_case_reason', '?')[:80]}")

# Action 准确率
action_correct = {"P0": [0, 0], "P1": [0, 0], "P2": [0, 0], "P3": [0, 0]}
for r in results:
    pri = r.get("priority", "?")
    if pri not in action_correct:
        continue
    action_correct[pri][1] += 1
    final = r["final_action"]
    if pri == "P0":
        if final == "transfer_human":
            action_correct[pri][0] += 1
    else:
        if final in ("answer", "clarify", "fallback_to_human"):
            action_correct[pri][0] += 1

print(f"\n[Action 准确率]")
for pri, (c, t) in action_correct.items():
    if t > 0:
        print(f"  {pri}: {c}/{t} = {c/t:.1%}")

# 总 span/event 数
print(f"\n[存储统计]")
print(f"  Traces: {q.count_traces()}")
with q._conn() as conn:
    span_count = conn.execute("SELECT COUNT(*) FROM spans").fetchone()[0]
    event_count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
print(f"  Spans: {span_count}")
print(f"  Events: {event_count}")

# 报告
report = {
    "version": "v3.9.0-observable-real",
    "run_date": time.strftime("%Y-%m-%dT%H:%M:%S"),
    "sample_size": len(samples),
    "total_elapsed_sec": round(total_elapsed, 1),
    "per_query_avg_ms": round(total_elapsed / len(samples) * 1000, 1),
    "layer_stats": q.layer_stats(),
    "p0_recall": q.p0_recall(),
    "bad_cases_count": len(bad_cases),
    "bad_cases": [{"trace_id": b["trace_id"], "reason": b.get("bad_case_reason"), "query": b["user_input"]} for b in bad_cases[:10]],
    "action_accuracy": {pri: {"correct": c, "total": t, "rate": c/t if t>0 else 0} for pri, (c, t) in action_correct.items()},
    "storage_stats": {
        "traces": q.count_traces(),
        "spans": span_count,
        "events": event_count,
    },
    "trace_ids": [r["trace_id"] for r in results],
}
report_path = _ROOT / "data" / "observable_v390_real_report.json"
report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n报告已保存: {report_path}")
print(f"SQLite: {_ROOT / 'data' / 'observability.db'}")
print(f"Viewer: {_ROOT / 'src' / 'observability' / 'viewer_server.py'}")