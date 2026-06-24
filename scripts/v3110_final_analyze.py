import json
import sqlite3
from collections import Counter
from pathlib import Path

_ROOT = Path(r'D:\Learning\AI\面试\AI智能客服')

# D v3.2
db_d32 = _ROOT / 'data' / 'observability_v3110_d32_regress.db'
c = sqlite3.connect(db_d32)
cur = c.cursor()
correct = Counter()
buckets = Counter()
p1_misjudged = []
p0_missed = []

for r in cur.execute("""
    SELECT user_input, priority, final_action FROM (
        SELECT user_input, priority, final_action,
               ROW_NUMBER() OVER (PARTITION BY user_input ORDER BY start_time DESC) rn
        FROM traces
    ) WHERE rn=1
"""):
    q, pri, final = r
    buckets[pri] += 1
    if pri == 'P0':
        if final == 'transfer_human':
            correct['P0'] += 1
        else:
            p0_missed.append((q, final))
    elif pri in ('P1', 'P2', 'P3'):
        if final in ('answer', 'clarify', 'fallback_to_human'):
            correct[pri] += 1
        else:
            if pri == 'P1':
                p1_misjudged.append((q, final))

print("=" * 70)
print("v3.11.0 FINAL on D v3.2 (按 query 最后一条统计)")
print("=" * 70)
for pri in ['P0', 'P1', 'P2', 'P3']:
    rate = correct[pri] / buckets[pri] * 100 if buckets[pri] > 0 else 0
    print(f"  {pri}: {correct[pri]}/{buckets[pri]} = {rate:.2f}%")

print(f"\nP0 missed ({len(p0_missed)}):")
for m in p0_missed[:10]:
    print(f"  [{m[1]}] {m[0][:80]}")

print(f"\nP1 misjudged (top 10 / total {len(p1_misjudged)}):")
for m in p1_misjudged[:10]:
    print(f"  [{m[1]}] {m[0][:80]}")

# D v3.3
db_d33 = _ROOT / 'data' / 'observability_v3110_full.db'
c2 = sqlite3.connect(db_d33)
cur2 = c2.cursor()
correct2 = Counter()
buckets2 = Counter()

for r in cur2.execute("""
    SELECT user_input, priority, final_action FROM (
        SELECT user_input, priority, final_action,
               ROW_NUMBER() OVER (PARTITION BY user_input ORDER BY start_time DESC) rn
        FROM traces
    ) WHERE rn=1
"""):
    q, pri, final = r
    buckets2[pri] += 1
    if pri == 'P0':
        if final == 'transfer_human':
            correct2['P0'] += 1
    elif pri in ('P1', 'P2', 'P3'):
        if final in ('answer', 'clarify', 'fallback_to_human'):
            correct2[pri] += 1

print()
print("=" * 70)
print("v3.11.0 FINAL on D v3.3 (按 query 最后一条统计)")
print("=" * 70)
for pri in ['P0', 'P1']:
    rate = correct2[pri] / buckets2[pri] * 100 if buckets2[pri] > 0 else 0
    print(f"  {pri}: {correct2[pri]}/{buckets2[pri]} = {rate:.2f}%")

# 写最终报告
report = {
    "version": "v3.11.0-FINAL-clean",
    "stats_method": "按 user_input 取最后一条 trace",
    "D_v3_2_dedup_1076": {
        "P0_accuracy": f"{correct['P0']}/{buckets['P0']} = {correct['P0']/buckets['P0']*100:.2f}%",
        "P1_accuracy": f"{correct['P1']}/{buckets['P1']} = {correct['P1']/buckets['P1']*100:.2f}%",
        "P2_accuracy": f"{correct['P2']}/{buckets['P2']} = {correct['P2']/buckets['P2']*100:.2f}%",
        "P3_accuracy": f"{correct['P3']}/{buckets['P3']} = {correct['P3']/buckets['P3']*100:.2f}%",
        "P1_misjudged_count": len(p1_misjudged),
        "P0_missed_count": len(p0_missed),
    },
    "D_v3_3_206": {
        "P0_accuracy": f"{correct2['P0']}/{buckets2['P0']} = {correct2['P0']/buckets2['P0']*100:.2f}%",
        "P1_accuracy": f"{correct2['P1']}/{buckets2['P1']} = {correct2['P1']/buckets2['P1']*100:.2f}%",
    },
}
out = _ROOT / 'data' / 'v3110_final_clean.json'
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(f"\n报告: {out}")
c.close()
c2.close()
