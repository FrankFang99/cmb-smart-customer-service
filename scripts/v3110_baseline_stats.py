"""v3.11.0 baseline report - 只统计, 不重跑 cascade"""
import json, sqlite3
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
db = _ROOT / "data" / "observability_v3110_baseline.db"
eval_path = _ROOT / "data" / "D_eval_set_v3.3.json"

p0_sub_map = {}
with open(eval_path, "r", encoding="utf-8") as f:
    raw = json.load(f)
for s in raw.get("samples", []):
    if s.get("is_p0"):
        p0_sub_map[s["question"].strip()] = s.get("p0_sub", "unknown") or "unknown"

c = sqlite3.connect(db)
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

p0_by_sub = {}
p0_missed_samples = []
for r in cur.execute("SELECT priority, final_action, p0_triggered, user_input FROM traces"):
    pri, final, triggered, q = r
    if pri != "P0":
        continue
    sub = p0_sub_map.get(q.strip(), "unknown")
    p0_by_sub.setdefault(sub, [0, 0])
    p0_by_sub[sub][1] += 1
    if triggered:
        p0_by_sub[sub][0] += 1
    else:
        p0_missed_samples.append({
            "sub": sub,
            "question": q[:100],
            "final_action": final,
        })

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

print(f"\nP0 missed 详情 ({len(p0_missed_samples)} 条):")
for m in p0_missed_samples[:20]:
    print(f"  [{m['sub']:15s}] {m['question']} → {m['final_action']}")

cur2 = c.cursor()
cur2.execute("SELECT COUNT(*) FROM traces WHERE is_bad_case=1")
bad_n = cur2.fetchone()[0]
print(f"\nBad Case: {bad_n} 条")

c.close()
