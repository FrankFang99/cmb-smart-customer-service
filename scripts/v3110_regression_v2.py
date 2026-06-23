import sqlite3, json
from collections import Counter

c = sqlite3.connect(r'D:\Learning\AI\面试\AI智能客服\data\observability_v3110_d32_regress.db')
cur = c.cursor()

# 按 query 取最后一条 trace, 重新统计
print("=" * 70)
print("v3.11.0 REGRESSION 真实统计 (按 query 最后一条 trace)")
print("=" * 70)

# 按 priority 算 buckets
buckets = Counter()
p0_recall = Counter()
p1_misjudged = []
p3_misjudged = []
p0_missed = []

for r in cur.execute("""
    SELECT user_input, priority, final_action, p0_triggered FROM (
        SELECT user_input, priority, final_action, p0_triggered,
               ROW_NUMBER() OVER (PARTITION BY user_input ORDER BY start_time DESC) rn
        FROM traces
    ) WHERE rn=1
"""):
    q, pri, final, p0t = r
    buckets[pri] += 1
    if pri == 'P0':
        if final == 'transfer_human':
            pass  # 正确
        else:
            p0_missed.append((q[:80], final))
    elif pri == 'P1':
        if final in ('answer', 'clarify', 'fallback_to_human'):
            pass  # 正确
        else:
            p1_misjudged.append((q[:80], final))
    elif pri == 'P3':
        if final in ('answer', 'clarify', 'fallback_to_human'):
            pass
        else:
            p3_misjudged.append((q[:80], final))

correct = {'P0': 0, 'P1': 0, 'P2': 0, 'P3': 0}
for r in cur.execute("""
    SELECT priority, final_action FROM (
        SELECT user_input, priority, final_action,
               ROW_NUMBER() OVER (PARTITION BY user_input ORDER BY start_time DESC) rn
        FROM traces
    ) WHERE rn=1
"""):
    pri, final = r
    if pri == 'P0' and final == 'transfer_human':
        correct[pri] += 1
    elif pri in ('P1', 'P2', 'P3') and final in ('answer', 'clarify', 'fallback_to_human'):
        correct[pri] += 1

for pri in ['P0', 'P1', 'P2', 'P3']:
    total = buckets[pri]
    c_count = correct[pri]
    rate = c_count / total * 100 if total > 0 else 0
    print(f"  {pri}: {c_count}/{total} = {rate:.2f}%")

# P0 召回
p0_triggered = cur.execute("""
    SELECT COUNT(*) FROM (
        SELECT user_input, p0_triggered,
               ROW_NUMBER() OVER (PARTITION BY user_input ORDER BY start_time DESC) rn
        FROM traces WHERE priority='P0'
    ) WHERE rn=1 AND p0_triggered=1
""").fetchone()[0]
p0_total = cur.execute("SELECT COUNT(*) FROM traces WHERE priority='P0'").fetchone()[0]
print(f"\n  P0 召回: {p0_triggered}/{p0_total} = {p0_triggered/p0_total*100:.2f}%")

print(f"\nP0 missed ({len(p0_missed)}):")
for m in p0_missed[:10]:
    print(f"  [{m[1]}] {m[0]}")

print(f"\nP1 误伤 ({len(p1_misjudged)}):")
for m in p1_misjudged[:30]:
    print(f"  [{m[1]}] {m[0]}")

print(f"\nP3 误伤 ({len(p3_misjudged)}):")
for m in p3_misjudged[:5]:
    print(f"  [{m[1]}] {m[0]}")

# 与 v3.10.1 对比
print()
print("=" * 70)
print("Regression 对比 v3.10.1 → v3.11.0 (按 query 正确统计)")
print("=" * 70)
v3101 = json.load(open(r'D:\Learning\AI\面试\AI智能客服\data\observable_v3101_full_report.json', encoding='utf-8'))
for pri in ['P0', 'P1', 'P2', 'P3']:
    v3101_acc = v3101['action_accuracy_full'][pri]['rate'] * 100
    new_acc = correct[pri] / buckets[pri] * 100 if buckets[pri] > 0 else 0
    delta = new_acc - v3101_acc
    flag = " ⚠️ REGRESSION" if delta < -1.0 else (" ✓" if delta >= 0 else " (minor)")
    print(f"  {pri}: {v3101_acc:.2f}% → {new_acc:.2f}% ({delta:+.2f}pp){flag}")

v3101_p0 = v3101['p0_recall']['P0']['recall_rate'] * 100
new_p0 = p0_triggered / p0_total * 100
print(f"\n  P0 召回: {v3101_p0:.2f}% → {new_p0:.2f}% ({new_p0 - v3101_p0:+.2f}pp)")

# 写最终 clean report
report = {
    "version": "v3.11.0-Round1-regression-on-D-v3.2-CLEAN",
    "stats_method": "按 user_input 取最后一条 trace (DISTINCT user_input = 1076)",
    "v3_10_1_baseline": v3101['action_accuracy_full'],
    "v3_11_0_round1": {
        pri: {"correct": correct[pri], "total": buckets[pri], "rate": correct[pri]/buckets[pri] if buckets[pri]>0 else 0}
        for pri in ['P0', 'P1', 'P2', 'P3']
    },
    "p0_recall_v3_11_0": f"{p0_triggered}/{p0_total}",
    "p1_misjudged_count": len(p1_misjudged),
    "p1_misjudged_samples": [{"q": m[0], "action": m[1]} for m in p1_misjudged],
    "p3_misjudged_count": len(p3_misjudged),
    "p0_missed_count": len(p0_missed),
}
report_path = r'D:\Learning\AI\面试\AI智能客服\data\v3110_regression_clean.json'
with open(report_path, 'w', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print(f"\n报告: {report_path}")

c.close()
