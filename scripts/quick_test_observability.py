"""
快速验证可观测平台 — 5 条测试 query (LLM 关闭, 快速跑)
"""
import sys
import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from src.agent.cascade_observable_v39 import ObservableCascadeV39
from src.observability.trace_query import TraceQuery
from src.observability.badcase_replayer import BadCaseReplayer

# 5 条快速验证 (LLM 关闭省 token)
test_queries = [
    ("我的信用卡丢了, 怎么办?", "P0"),
    ("信用卡年费多少?", "P1"),
    ("今天上海天气怎么样", "P2"),
    ("谢谢", "P3"),
    ("我好像被骗了, 转了 5 万", "P0"),
]

cascade = ObservableCascadeV39(enable_llm=False, confidence_threshold=0.85)
print("Running 5 test queries (LLM disabled for speed)...")
for i, (q, pri) in enumerate(test_queries, 1):
    result = cascade.handle(
        q,
        priority=pri,
        expected_action="transfer_human" if pri == "P0" else "answer",
    )
    print(
        f"[{i}] [{pri}] {q[:30]} -> {result['final_action']} "
        f"(spans={result.get('span_count', 0)}, {result['elapsed_ms']}ms)"
    )

# 查询统计
q = TraceQuery()
print("\n[Layer Stats]")
for layer, s in q.layer_stats().items():
    print(f"  {layer}: {s['count']}次, avg {s['avg_elapsed_ms']}ms")

print("\n[Traces in DB]:", q.count_traces())

# Bad Case 自动检测
bad = q.list_traces(is_bad_case=True, limit=10)
print(f"\n[Auto-detected Bad Cases]: {len(bad)}")
for b in bad[:3]:
    print(f"  - {b['trace_id']}: {b.get('bad_case_reason', '?')[:80]}")

# 找一个 trace 还原
trace_id = q.list_traces(limit=1)[0]["trace_id"]
print(f"\n[Replay trace]: {trace_id}")
replayer = BadCaseReplayer()
report = replayer.replay(trace_id)
print("\n=== 案发现场报告 (Markdown 预览前 1000 字) ===")
print(report.to_markdown()[:1000])
print("\n=== === ===")