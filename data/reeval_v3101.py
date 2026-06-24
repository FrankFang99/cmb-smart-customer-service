"""Re-evaluate v3.10.1 P1 with v3.10.0 report's coarse-grain action rule"""
import sqlite3
from pathlib import Path
DB = Path(r"D:\Learning\AI\面试\AI智能客服\data\observability_v3101.db")
c = sqlite3.connect(DB)
cur = c.cursor()

# v3.10.0 报告口径: P0 期望 transfer_human, P1/P2/P3 期望 answer/clarify/fallback_to_human
buckets = {"P0": [0, 0], "P1": [0, 0], "P2": [0, 0], "P3": [0, 0]}
for r in cur.execute("SELECT priority, final_action FROM traces"):
    pri, final = r[0], r[1]
    if pri not in buckets: continue
    buckets[pri][1] += 1
    if pri == "P0":
        if final == "transfer_human": buckets[pri][0] += 1
    else:
        if final in ("answer", "clarify", "fallback_to_human"): buckets[pri][0] += 1

print("=" * 70)
print("v3.10.1 报告口径重算 (粗粒度, 同 v3.10.0 报告):")
print("=" * 70)
for pri, (c, t) in buckets.items():
    rate = c/t*100 if t > 0 else 0
    print(f"  {pri}: {c}/{t} = {rate:.2f}%")

# 对比 v3.10.0 全量 (来自 observable_v390_full_report.json)
print()
print("v3.10.0 全量 (1076 条去重版) 对比:")
print("  P0: 431/431 = 100.00%")
print("  P1: 230/332 = 69.28%")
print("  P2: 141/155 = 90.97%")
print("  P3: 158/158 = 100.00%")
print()
print("v3.10.1 P1 提升 (pp):")
diff = buckets["P1"][0] - 230
print(f"  P1 提升: {diff} 条 = {diff/332*100:.2f}pp (从 69.28% → {buckets['P1'][0]/332*100:.2f}%)")
