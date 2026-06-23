"""v3.11.0 baseline (Round 1, 关键步骤)
====================================
【目标】
在 D v3.3 新样本 (206 条) 上跑 v3.10.1 patch, 验证:
1. v3.10.1 patch 在真实未见样本上 P0 召回是否仍然 ≥95%
2. P1 误伤率在新样本上如何
3. 哪些 P0 子类漏检最多 → Round 1 patch 重点修复

【关键】这是 loop engineering 的「先测基线」步骤, 不修改任何 patch,
      目的是看 v3.10.1 patch 是不是真的过拟合了。
"""
import sys, json, time, os, hashlib, sqlite3
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

# 用独立 db 跑 v3.11.0-baseline, 不污染 v3.10.1 全量数据
from src.observability.trace_recorder import TraceRecorder
import src.observability.trace_recorder as _tr_mod
new_db = _ROOT / "data" / "observability_v3110_baseline.db"
_tr_mod._recorder_singleton = TraceRecorder(db_path=new_db)
print(f"✓ v3.11.0 baseline db: {new_db.name}")

from src.agent.cascade_observable_v39 import ObservableCascadeV39

print("=" * 70)
print("v3.11.0 BASELINE — D v3.3 新样本 (206 条, v3.10.1 patch 不变)")
print("=" * 70)

eval_path = _ROOT / "data" / "D_eval_set_v3.3.json"
with open(eval_path, "r", encoding="utf-8") as f:
    eval_data = json.load(f)
samples = eval_data.get("samples", [])
p0_count = sum(1 for s in samples if s.get("is_p0"))
print(f"\n样本: {len(samples)} 条 (P0={p0_count}, 非P0={len(samples)-p0_count})")

os.environ.setdefault("MINIMAX_MODEL", "MiniMax-M2.7")
# 用 v3.10.1 patch (用户当前线上版本, 不动)
cascade = ObservableCascadeV39(enable_llm=True, confidence_threshold=0.85)

t0 = time.time()
processed = 0
errors = []

for i, item in enumerate(samples):
    query = item.get("question", "").strip()
    if not query:
        continue
    # D v3.3 用 is_p0 + intent, 转换为 v3.10.1 评测格式
    is_p0 = item.get("is_p0", False)
    pri = "P0" if is_p0 else "P1"  # 默认归 P1 (v3.10.1 不分 P2/P3, 按业务粗粒度)
    intent = item.get("intent", "?")
    expected_action = "transfer_human" if is_p0 else "answer"

    seed = f"tr_v3110_b_" + hashlib.md5(query.encode("utf-8")).hexdigest()[:12]
    try:
        cascade.handle(
            user_input=query,
            session_id=seed,
            priority=pri,
            expected_action=expected_action,
            intent_top1=intent,
        )
    except Exception as e:
        errors.append((query, str(e)))

    processed += 1
    if (i + 1) % 50 == 0:
        elapsed = time.time() - t0
        rate = (i + 1) / elapsed
        eta = (len(samples) - i - 1) / rate if rate > 0 else 0
        print(f"  [{i+1}/{len(samples)}] 累计 {elapsed:.0f}s, 预计剩余 {eta:.0f}s")

elapsed = time.time() - t0
print(f"\n✓ 跑完: {processed} 条 / 耗时 {elapsed:.0f}s / 错误 {len(errors)}")

# 统计
c = sqlite3.connect(new_db)
cur = c.cursor()
buckets = {"P0": [0, 0], "P1": [0, 0]}
for r in cur.execute("SELECT priority, final_action FROM traces"):
    pri, final = r[0], r[1]
    if pri not in buckets:
        continue
    buckets[pri][1] += 1
    if pri == "P0":
        if final == "transfer_human":
            buckets[pri][0] += 1
    else:
        if final in ("answer", "clarify", "fallback_to_human"):
            buckets[pri][0] += 1

# P0 召回 (按子类别细分 - 从 D v3.3 重新读 question→p0_sub 映射, 不依赖 traces 表)
p0_sub_map = {}
with open(eval_path, "r", encoding="utf-8") as f:
    raw = json.load(f)
for s in raw.get("samples", []):
    if s.get("is_p0"):
        p0_sub_map[s["question"].strip()] = s.get("p0_sub", "unknown") or "unknown"

p0_by_sub = {}
for r in cur.execute("SELECT priority, final_action, p0_triggered, user_input FROM traces"):
    pri, final, triggered, q = r
    if pri != "P0":
        continue
    sub = p0_sub_map.get(q.strip(), "unknown")
    p0_by_sub.setdefault(sub, [0, 0])
    p0_by_sub[sub][1] += 1
    if triggered:
        p0_by_sub[sub][0] += 1

print()
print("=" * 70)
print("v3.10.1 在 D v3.3 新样本上的基线表现 (Round 1 起点)")
print("=" * 70)
for pri, (correct, total) in buckets.items():
    rate = correct / total * 100 if total > 0 else 0
    print(f"  {pri}: {correct}/{total} = {rate:.2f}%")
print()
print("P0 召回 (按子类):")
for sub, (correct, total) in sorted(p0_by_sub.items(), key=lambda x: -x[1][1]):
    rate = correct / total * 100 if total > 0 else 0
    flag = " ⚠️ OVERFIT" if rate < 90 else ""
    print(f"  {sub:20s} {correct}/{total} = {rate:.2f}%{flag}")

cur2 = c.cursor()
cur2.execute("SELECT COUNT(*) FROM traces WHERE is_bad_case=1")
bad_n = cur2.fetchone()[0]
print(f"\nBad Case: {bad_n} 条")

# 写报告
report = {
    "version": "v3.11.0-baseline-on-D-v3.3",
    "run_date": time.strftime("%Y-%m-%dT%H:%M:%S"),
    "eval_set": "D_eval_set_v3.3.json (Round 1 扩充, 206 条全新样本)",
    "patch_under_test": "v3.10.1 (无修改, 用于测基线)",
    "total_elapsed_sec": round(elapsed, 1),
    "action_accuracy_full": {pri: {"correct": c, "total": t, "rate": c/t if t>0 else 0} for pri, (c, t) in buckets.items()},
    "p0_recall_by_sub": {sub: {"correct": c, "total": t, "rate": c/t if t>0 else 0} for sub, (c, t) in p0_by_sub.items()},
    "bad_cases_count": bad_n,
}
report_path = _ROOT / "data" / "v3110_baseline_report.json"
report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n报告: {report_path}")
c.close()
