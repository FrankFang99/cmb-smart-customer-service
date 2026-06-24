"""
1500 条全量可观测评测 — 全链路 Trace 入库
"""
import sys
import json
import time
import os
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from src.agent.cascade_observable_v39 import ObservableCascadeV39
from src.observability.trace_query import TraceQuery

print("=" * 70)
print("可观测平台 v3.9.0 — 1500 条全量真跑")
print("=" * 70)

# 加载测试集 (v3.10.0 用去重版, 避免重复样本污染 + 防止 patch 过拟合)
eval_path = _ROOT / "data" / "D_eval_set_v3.2_dedup.json"
if not eval_path.exists():
    eval_path = _ROOT / "data" / "D_eval_set_v3.2.json"
    print(f"⚠️  去重版不存在, 用原始版本: {eval_path.name}")
else:
    print(f"✓ 使用去重版评测集: {eval_path.name}")
with open(eval_path, "r", encoding="utf-8") as f:
    eval_data = json.load(f)
eval_items = eval_data.get("samples", []) if isinstance(eval_data, dict) else eval_data

# 按 priority 分层, 全跑
p0 = [s for s in eval_items if s.get("priority") == "P0"]
p1 = [s for s in eval_items if s.get("priority") == "P1"]
p2 = [s for s in eval_items if s.get("priority") == "P2"]
p3 = [s for s in eval_items if s.get("priority") == "P3"]
samples = p0 + p1 + p2 + p3

print(f"\n全量样本: P0:{len(p0)} P1:{len(p1)} P2:{len(p2)} P3:{len(p3)} = {len(samples)} 条")

# 断点续跑检查: 已经入库的 trace 不再跑
q = TraceQuery()
existing_count = q.count_traces()
existing_trace_ids = set()
if existing_count > 0:
    existing_trace_ids = {t["trace_id"] for t in q.list_traces(limit=existing_count)}
print(f"已入库 trace: {existing_count} 条 (断点续跑跳过)")

# LLM 配置
os.environ.setdefault("MINIMAX_MODEL", "MiniMax-M2.7")
print(f"LLM 模型: {os.environ.get('MINIMAX_MODEL')}")

# 实例化 Cascade
cascade = ObservableCascadeV39(enable_llm=True, confidence_threshold=0.85)

print(f"\n开始全量跑 (按 priority 顺序: P0 → P1 → P2 → P3)...\n")
t0 = time.time()
results = []
processed = 0
skipped = 0
errors = []

# 给每条 query 加稳定 trace_id (基于 query 文本 hash), 这样续跑才能匹配
import hashlib
def _stable_trace_seed(query: str) -> str:
    return "tr_" + hashlib.md5(query.encode("utf-8")).hexdigest()[:12]

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

    seed = _stable_trace_seed(query)

    # 断点续跑: 已入库跳过
    if seed in existing_trace_ids:
        skipped += 1
        continue

    try:
        result = cascade.handle(
            query, priority=priority,
            expected_action=expected, intent_top1=intent_top1,
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
        processed += 1

        # 每 100 条打印一次进度
        total_done = processed + skipped
        if processed % 50 == 0:
            elapsed = time.time() - t0
            avg_per = elapsed / processed if processed else 0
            remaining = (len(samples) - total_done) * avg_per
            print(
                f"[进度] {total_done}/{len(samples)} ({total_done/len(samples)*100:.1f}%) | "
                f"本批 {processed} 条 | 累计 {elapsed:.1f}s | "
                f"预计剩余 {remaining/60:.1f}min"
            )
    except Exception as e:
        errors.append({"query": query[:50], "error": str(e)[:200]})
        print(f"  ❌ [{i+1}] error: {str(e)[:100]}")

# 收尾
total_elapsed = time.time() - t0
print(f"\n{'='*70}")
print(f"全量跑完成!")
print(f"  新增入库: {processed} 条")
print(f"  跳过(已入库): {skipped} 条")
print(f"  错误: {len(errors)} 条")
print(f"  本次耗时: {total_elapsed:.1f}s ({total_elapsed/60:.1f}min)")

# 最终统计
q = TraceQuery()
total = q.count_traces()
print(f"\n[全量统计]")
print(f"  DB 总 traces: {total} 条")
print(f"\n[各层调用统计]")
for layer, s in q.layer_stats().items():
    print(f"  {layer}: {s['count']}次, 平均{s['avg_elapsed_ms']:.1f}ms, 错误{s['error_count']}")

print(f"\n[P0 召回]")
for pri, s in q.p0_recall().items():
    print(f"  {pri}: {s['p0_caught']}/{s['total']} = {s['recall_rate']:.1%}")

# Bad Case
bad_cases = q.list_traces(is_bad_case=True, limit=20)
print(f"\n[自动检测 Bad Case]: {len(bad_cases)} 条")
for bc in bad_cases[:5]:
    print(f"  - {bc['trace_id']}: {bc.get('bad_case_reason', '?')[:80]}")

# Action 准确率 (全量重算)
all_traces = q.list_traces(limit=100000)
action_correct = {"P0": [0, 0], "P1": [0, 0], "P2": [0, 0], "P3": [0, 0]}
for t in all_traces:
    pri = t.get("priority", "?")
    if pri not in action_correct:
        continue
    action_correct[pri][1] += 1
    final = t["final_action"]
    if pri == "P0":
        if final == "transfer_human":
            action_correct[pri][0] += 1
    else:
        if final in ("answer", "clarify", "fallback_to_human"):
            action_correct[pri][0] += 1

print(f"\n[Action 准确率 (全量)]")
for pri, (c, t) in action_correct.items():
    if t > 0:
        print(f"  {pri}: {c}/{t} = {c/t:.1%}")

# 存储统计
with q._conn() as conn:
    span_count = conn.execute("SELECT COUNT(*) FROM spans").fetchone()[0]
    event_count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
print(f"\n[存储统计]")
print(f"  Traces: {total}")
print(f"  Spans: {span_count}")
print(f"  Events: {event_count}")
print(f"  DB 大小: {(_ROOT / 'data' / 'observability.db').stat().st_size / 1024:.1f} KB")

# 报告
report = {
    "version": "v3.9.0-full-1500",
    "run_date": time.strftime("%Y-%m-%dT%H:%M:%S"),
    "sample_size": len(samples),
    "processed": processed,
    "skipped": skipped,
    "errors_count": len(errors),
    "total_elapsed_sec": round(total_elapsed, 1),
    "per_query_avg_ms": round(total_elapsed / max(processed, 1) * 1000, 1),
    "layer_stats": q.layer_stats(),
    "p0_recall": q.p0_recall(),
    "bad_cases_count": len(bad_cases),
    "bad_cases_sample": [{"trace_id": b["trace_id"], "reason": b.get("bad_case_reason"), "query": b["user_input"]} for b in bad_cases[:10]],
    "action_accuracy_full": {pri: {"correct": c, "total": t, "rate": c/t if t>0 else 0} for pri, (c, t) in action_correct.items()},
    "storage_stats": {"traces": total, "spans": span_count, "events": event_count},
}
report_path = _ROOT / "data" / "observable_v390_full_report.json"
report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n报告: {report_path}")
print(f"SQLite: {_ROOT / 'data' / 'observability.db'}")