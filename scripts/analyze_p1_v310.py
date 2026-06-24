"""P1 error analysis: compare v3.10.0 final_action vs expected_action."""
import sqlite3, json
from collections import Counter, defaultdict

DB = r"D:\Learning\AI\面试\AI智能客服\data\observability.db"
c = sqlite3.connect(DB)
cur = c.cursor()

# 1) P1 confusion: actual vs expected action, with p0_triggered
print("=" * 70)
print("[P1 全量 - 整体分布]")
cur.execute("SELECT final_action, expected_action, p0_triggered, COUNT(*) FROM traces WHERE priority='P1' GROUP BY final_action, expected_action, p0_triggered ORDER BY 4 DESC")
rows = cur.fetchall()
for r in rows:
    print(f"  {r[0]:25s} -> exp {r[1]:25s} | p0={r[2]} | n={r[3]}")

# 2) P1 wrong cases only - sample by action pair
print()
print("=" * 70)
print("[P1 错误样本 - 按 (实际, 期望) 归类]")
cur.execute("""
SELECT user_input, final_action, expected_action, p0_triggered, final_intent, intent_top1, trace_id
FROM traces
WHERE priority='P1' AND final_action != expected_action
ORDER BY p0_triggered DESC, final_action
""")
wrong = cur.fetchall()
print(f"Total P1 wrong: {len(wrong)}")
print()
# Group by (final, expected, p0)
groups = defaultdict(list)
for w in wrong:
    key = (w[1], w[2], w[3])
    groups[key].append(w)

for key, items in sorted(groups.items(), key=lambda x: -len(x[1])):
    fa, ea, p0 = key
    print(f"\n--- final={fa} | expected={ea} | p0_triggered={p0} | n={len(items)} ---")
    for w in items[:5]:
        print(f"  Q: {w[0][:50]}")
        print(f"     intent={w[4]} | intent_top1={w[5]}")

# 3) P1 wrong + p0_triggered=1 — 这些是 patch 误伤的候选
print()
print("=" * 70)
print("[P1 错误 + p0_triggered=1 —— v3.10.0 patch 误伤候选]")
cur.execute("""
SELECT user_input, final_action, expected_action, p0_triggered, final_intent
FROM traces
WHERE priority='P1' AND final_action != expected_action AND p0_triggered=1
""")
hit = cur.fetchall()
print(f"n={len(hit)}")
for w in hit[:30]:
    print(f"  Q: {w[0][:55]}")
    print(f"     final={w[1]} | expected={w[2]} | intent={w[4]}")

c.close()
