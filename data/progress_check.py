"""Check v3.10.1 progress + identify the 1 P0 missed"""
import sqlite3
from pathlib import Path
DB = Path(r"D:\Learning\AI\面试\AI智能客服\data\observability_v3101_full.db")
c = sqlite3.connect(DB)
cur = c.cursor()
print("P0 missed (p0_triggered=0):")
for r in cur.execute("SELECT user_input, final_action, final_intent FROM traces WHERE priority='P0' AND p0_triggered=0"):
    print(f"  Q: {r[0]}")
    print(f"     final_action={r[1]}  final_intent={r[2]}")
print()
print("P0 not-transfer_human:")
for r in cur.execute("SELECT user_input, final_action FROM traces WHERE priority='P0' AND final_action != 'transfer_human'"):
    print(f"  Q: {r[0]}")
    print(f"     final_action={r[1]}")
print()
print("P0 counts:")
_total = cur.execute("SELECT COUNT(*) FROM traces WHERE priority='P0'").fetchone()[0]
_th = cur.execute("SELECT COUNT(*) FROM traces WHERE priority='P0' AND final_action='transfer_human'").fetchone()[0]
_pt = cur.execute("SELECT COUNT(*) FROM traces WHERE priority='P0' AND p0_triggered=1").fetchone()[0]
print(f"  total: {_total}")
print(f"  transfer_human: {_th}")
print(f"  p0_triggered=1: {_pt}")
print()
print("Total progress:")
for r in cur.execute("SELECT priority, COUNT(*) FROM traces GROUP BY priority ORDER BY 1"):
    print(f"  {r[0]}: {r[1]}")
print(f"  Total: {cur.execute('SELECT COUNT(*) FROM traces').fetchone()[0]}")
