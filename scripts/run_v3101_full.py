"""v3.10.1 全量跑 (1076 条) - 验证 P0=100% 不破 + 完整 P1/P2/P3 数字
备份原 observability.db 后写入新 db, 不破坏 v3.10.0 数据
"""
import sys, json, time, os, hashlib, shutil
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

# 备份原 db (v3.10.0 全量结果, 不能覆盖)
src_db = _ROOT / "data" / "observability.db"
bak_db = _ROOT / "data" / "observability.v3100.bak.db"
if not bak_db.exists():
    shutil.copy(src_db, bak_db)
    print(f"✓ 备份 v3.10.0 db -> {bak_db.name}")
else:
    print(f"✓ v3.10.0 db 备份已存在: {bak_db.name}")

# 用独立 db 跑 v3.10.1, 不污染 v3.10.0 全量数据
from src.observability.trace_recorder import TraceRecorder
import src.observability.trace_recorder as _tr_mod
new_db = _ROOT / "data" / "observability_v3101_full.db"
_tr_mod._recorder_singleton = TraceRecorder(db_path=new_db)
print(f"✓ v3.10.1 db: {new_db.name}")

from src.agent.cascade_observable_v39 import ObservableCascadeV39

print("=" * 70)
print("v3.10.1 — 全量 1076 条 (P0 + P1 + P2 + P3)")
print("=" * 70)

eval_path = _ROOT / "data" / "D_eval_set_v3.2_dedup.json"
with open(eval_path, "r", encoding="utf-8") as f:
    eval_data = json.load(f)
eval_items = eval_data.get("samples", []) if isinstance(eval_data, dict) else eval_data
p0 = [s for s in eval_items if s.get("priority") == "P0"]
p1 = [s for s in eval_items if s.get("priority") == "P1"]
p2 = [s for s in eval_items if s.get("priority") == "P2"]
p3 = [s for s in eval_items if s.get("priority") == "P3"]
samples = p0 + p1 + p2 + p3
print(f"\n样本分布: P0:{len(p0)} P1:{len(p1)} P2:{len(p2)} P3:{len(p3)} = {len(samples)} 条")

os.environ.setdefault("MINIMAX_MODEL", "MiniMax-M2.7")
cascade = ObservableCascadeV39(enable_llm=True, confidence_threshold=0.85)

def _stable_trace_seed(query: str, pri: str) -> str:
    return f"tr_v3101_{pri}_" + hashlib.md5(query.encode("utf-8")).hexdigest()[:12]

t0 = time.time()
processed = 0
errors = []

for i, item in enumerate(samples):
    query = item.get("query") or item.get("text") or str(item)
    expected = item.get("expected_action") or item.get("label") or "unknown"
    pri = item.get("priority", "?")
    intent_top1 = item.get("intent_top1", "?")
    seed = _stable_trace_seed(query, pri)

    try:
        cascade.handle(
            user_input=query,
            session_id=seed,
            priority=pri,
            expected_action=expected,
            intent_top1=intent_top1,
        )
    except Exception as e:
        errors.append((query, str(e)))

    processed += 1
    if (i + 1) % 100 == 0:
        elapsed = time.time() - t0
        rate = (i + 1) / elapsed
        eta = (len(samples) - i - 1) / rate if rate > 0 else 0
        print(f"  [{i+1}/{len(samples)}] 累计 {elapsed:.0f}s, 预计剩余 {eta:.0f}s")

elapsed = time.time() - t0
print(f"\n✓ 全量跑完: {processed} 条 / 耗时 {elapsed:.0f}s / 错误 {len(errors)}")

# 统计 (用 v3.10.0 报告的粗粒度规则)
import sqlite3
c = sqlite3.connect(new_db)
cur = c.cursor()
buckets = {"P0": [0, 0], "P1": [0, 0], "P2": [0, 0], "P3": [0, 0]}
for r in cur.execute("SELECT priority, final_action FROM traces"):
    pri, final = r[0], r[1]
    if pri not in buckets: continue
    buckets[pri][1] += 1
    if pri == "P0":
        if final == "transfer_human": buckets[pri][0] += 1
    else:
        if final in ("answer", "clarify", "fallback_to_human"): buckets[pri][0] += 1

# P0 召回 (用 v3.10.0 报告口径: P0 trigger 比例)
p0_recall = {}
for pri in ["P0", "P1", "P2", "P3"]:
    cur2 = c.cursor()
    cur2.execute("SELECT COUNT(*) FROM traces WHERE priority=? AND p0_triggered=1", (pri,))
    triggered = cur2.fetchone()[0]
    cur2.execute("SELECT COUNT(*) FROM traces WHERE priority=?", (pri,))
    total = cur2.fetchone()[0]
    p0_recall[pri] = {"total": total, "p0_caught": triggered, "recall_rate": triggered/total if total>0 else 0}

# Bad case 自动检测
cur2 = c.cursor()
cur2.execute("SELECT COUNT(*) FROM traces WHERE is_bad_case=1")
bad_n = cur2.fetchone()[0]

print()
print("=" * 70)
print("v3.10.1 全量结果 (粗粒度, 同 v3.10.0 报告):")
print("=" * 70)
for pri, (correct, total) in buckets.items():
    rate = correct/total*100 if total > 0 else 0
    print(f"  {pri}: {correct}/{total} = {rate:.2f}%")
print()
print("P0 召回:")
for pri, r in p0_recall.items():
    print(f"  {pri}: {r['p0_caught']}/{r['total']} = {r['recall_rate']*100:.2f}%")
print()
print(f"Bad Case (自动检测): {bad_n} 条")

# 写报告
report = {
    "version": "v3.10.1-full-1076-dedup",
    "run_date": time.strftime("%Y-%m-%dT%H:%M:%S"),
    "sample_size": len(samples),
    "processed": processed,
    "errors_count": len(errors),
    "total_elapsed_sec": round(elapsed, 1),
    "action_accuracy_full": {pri: {"correct": c, "total": t, "rate": c/t if t>0 else 0} for pri, (c, t) in buckets.items()},
    "p0_recall": p0_recall,
    "bad_cases_count": bad_n,
}
report_path = _ROOT / "data" / "observable_v3101_full_report.json"
report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n报告: {report_path}")
c.close()
