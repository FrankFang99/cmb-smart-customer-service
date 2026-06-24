"""Compare v3.10.0 vs v3.10.1 for '给国外汇钱'"""
import sqlite3
from pathlib import Path
DB_3100 = Path(r"D:\Learning\AI\面试\AI智能客服\data\observability.db")
DB_3101 = Path(r"D:\Learning\AI\面试\AI智能客服\data\observability_v3101_full.db")
c1 = sqlite3.connect(DB_3100); c2 = sqlite3.connect(DB_3101)

for label, c in [("v3.10.0", c1), ("v3.10.1", c2)]:
    cur = c.cursor()
    print(f"=== {label} '给国外汇钱' ===")
    for r in cur.execute("SELECT priority, final_action, final_intent, p0_triggered, intent_top1 FROM traces WHERE user_input='给国外汇钱'"):
        print(f"  pri={r[0]} final={r[1]} intent={r[2]} p0={r[3]} intent_top1={r[4]}")
    print()
