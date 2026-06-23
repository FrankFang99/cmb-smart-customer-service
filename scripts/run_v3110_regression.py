"""v3.11.0 regression check - 在 D v3.2 上验证 patch 不破 v3.10.1 表现"""
import sys, json, time, os, hashlib, sqlite3
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from src.observability.trace_recorder import TraceRecorder
import src.observability.trace_recorder as _tr_mod
new_db = _ROOT / "data" / "observability_v3110_d32_regress.db"
_tr_mod._recorder_singleton = TraceRecorder(db_path=new_db)
print(f"✓ regression db: {new_db.name}")

from src.agent.cascade_observable_v39 import ObservableCascadeV39

print("=" * 70)
print("v3.11.0 REGRESSION CHECK — D v3.2 dedup (1076 条)")
print("=" * 70)

eval_path = _ROOT / "data" / "D_eval_set_v3.2_dedup.json"
with open(eval_path, "r", encoding="utf-8") as f:
    eval_data = json.load(f)
samples = eval_data.get("samples", []) if isinstance(eval_data, dict) else eval_data
p0 = [s for s in samples if s.get("priority") == "P0"]
p1 = [s for s in samples if s.get("priority") == "P1"]
p2 = [s for s in samples if s.get("priority") == "P2"]
p3 = [s for s in samples if s.get("priority") == "P3"]
ordered = p0 + p1 + p2 + p3
print(f"\n样本: P0:{len(p0)} P1:{len(p1)} P2:{len(p2)} P3:{len(p3)} = {len(ordered)} 条")

os.environ.setdefault("MINIMAX_MODEL", "MiniMax-M2.7")
cascade = ObservableCascadeV39(enable_llm=True, confidence_threshold=0.85)

t0 = time.time()
processed = 0

for i, item in enumerate(ordered):
    query = item.get("query") or item.get("text") or ""
    if not query:
        continue
    pri = item.get("priority", "?")
    expected = item.get("expected_action") or "unknown"
    intent_top1 = item.get("intent_top1", "?")
    seed = f"tr_v3110_reg_{pri}_" + hashlib.md5(query.encode("utf-8")).hexdigest()[:12]
    try:
        cascade.handle(
            user_input=query,
            session_id=seed,
            priority=pri,
            expected_action=expected,
            intent_top1=intent_top1,
        )
    except Exception as e:
        pass

    processed += 1
    if (i + 1) % 100 == 0:
        elapsed = time.time() - t0
        rate = (i + 1) / elapsed
        eta = (len(ordered) - i - 1) / rate if rate > 0 else 0
        print(f"  [{i+1}/{len(ordered)}] 累计 {elapsed:.0f}s, 预计剩余 {eta:.0f}s")

elapsed = time.time() - t0
print(f"\n✓ 跑完: {processed} 条 / 耗时 {elapsed:.0f}s")

c = sqlite3.connect(new_db)
cur = c.cursor()
buckets = {"P0": [0, 0], "P1": [0, 0], "P2": [0, 0], "P3": [0, 0]}
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

p0_recall = {}
for pri in ["P0", "P1", "P2", "P3"]:
    cur2 = c.cursor()
    cur2.execute("SELECT COUNT(*) FROM traces WHERE priority=? AND p0_triggered=1", (pri,))
    triggered = cur2.fetchone()[0]
    cur2.execute("SELECT COUNT(*) FROM traces WHERE priority=?", (pri,))
    total = cur2.fetchone()[0]
    p0_recall[pri] = {"total": total, "p0_caught": triggered, "recall_rate": triggered/total if total > 0 else 0}

cur2 = c.cursor()
cur2.execute("SELECT COUNT(*) FROM traces WHERE is_bad_case=1")
bad_n = cur2.fetchone()[0]

print()
print("=" * 70)
print("v3.11.0 REGRESSION ON D v3.2")
print("=" * 70)
for pri, (correct, total) in buckets.items():
    rate = correct / total * 100 if total > 0 else 0
    print(f"  {pri}: {correct}/{total} = {rate:.2f}%")
print()
print("P0 召回:")
for pri, r in p0_recall.items():
    print(f"  {pri}: {r['p0_caught']}/{r['total']} = {r['recall_rate']*100:.2f}%")
print(f"\nBad Case: {bad_n} 条")

# 与 v3.10.1 full 对比
v3101_path = _ROOT / "data" / "observable_v3101_full_report.json"
if v3101_path.exists():
    v3101 = json.loads(v3101_path.read_text(encoding="utf-8"))
    print()
    print("=" * 70)
    print("Regression 对比: v3.10.1 → v3.11.0 (D v3.2 上不破)")
    print("=" * 70)
    for pri in ["P0", "P1", "P2", "P3"]:
        v3101_acc = v3101.get("action_accuracy_full", {}).get(pri, {}).get("rate", 0) * 100
        v3110_acc = buckets[pri][0] / buckets[pri][1] * 100 if buckets[pri][1] > 0 else 0
        delta = v3110_acc - v3101_acc
        flag = " ⚠️ REGRESSION" if delta < -1.0 else ""
        print(f"  {pri} 准确: {v3101_acc:.2f}% → {v3110_acc:.2f}% ({delta:+.2f}pp){flag}")
    v3101_p0 = v3101.get("p0_recall", {}).get("P0", {}).get("recall_rate", 0) * 100
    v3110_p0 = p0_recall["P0"]["recall_rate"] * 100
    print(f"\n  P0 召回: {v3101_p0:.2f}% → {v3110_p0:.2f}% ({v3110_p0 - v3101_p0:+.2f}pp)")

c.close()
