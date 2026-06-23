import json
import sqlite3
from collections import Counter
from pathlib import Path

_ROOT = Path(r'D:\Learning\AI\面试\AI智能客服')
db = _ROOT / 'data' / 'observability_v3110_d32_regress.db'

c = sqlite3.connect(db)
cur = c.cursor()

# 按 query 最后一条 trace 统计
correct = Counter()
buckets = Counter()
p1_misjudged = []
p0_missed = []
freeze_misjudge = []
aml_misjudge = []

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
                # freeze 误伤 (含 "被冻/冻结/被锁/状态异常")
                if any(kw in q for kw in ['被冻', '冻结', '被锁', '状态异常']):
                    freeze_misjudge.append(q)
                # AML 误伤 (含 "理财/存单/密码/影票/定投/开指纹")
                elif any(kw in q for kw in ['理财', '存单', '密码', '影票', '定投', '开指纹', '信用卡']):
                    aml_misjudge.append(q)

print("=" * 70)
print("Round 2 D v3.2 真实统计 (按 query 最后一条)")
print("=" * 70)
for pri in ['P0', 'P1', 'P2', 'P3']:
    rate = correct[pri] / buckets[pri] * 100 if buckets[pri] > 0 else 0
    print(f"  {pri}: {correct[pri]}/{buckets[pri]} = {rate:.2f}%")

print(f"\nP1 误伤 {len(p1_misjudged)}:")
for m in p1_misjudged:
    print(f"  [{m[1]}] {m[0][:80]}")

print(f"\n  freeze 误伤子集 ({len(freeze_misjudge)}):")
for q in freeze_misjudge[:10]:
    print(f"    {q}")

print(f"  AML/其他误伤子集 ({len(aml_misjudge)}):")
for q in aml_misjudge[:10]:
    print(f"    {q}")

# 对比
print()
print("=" * 70)
print("三版本对比")
print("=" * 70)
v3101 = json.load(open(_ROOT / 'data' / 'observable_v3101_full_report.json', encoding='utf-8'))
v_r1_p1 = 71.99  # Round 1 实测
print(f"  v3.10.1 P0: 99.77%, P1: 72.89%")
print(f"  Round 1 P0: 100%,  P1: {v_r1_p1}% (P1 误伤 93)")
print(f"  Round 2 P0: 100%,  P1: {correct['P1']/buckets['P1']*100:.2f}% (P1 误伤 {len(p1_misjudged)})")
delta_p1 = correct['P1']/buckets['P1']*100 - v_r1_p1
print(f"  R2 vs R1 P1: {delta_p1:+.2f}pp")

# 写最终 Round 2 报告
report = {
    "version": "v3.11.0-Round2-final",
    "eval_set": "D_eval_set_v3.2_dedup.json (1076 条)",
    "stats_method": "按 user_input 取最后一条 trace",
    "p0_accuracy": f"{correct['P0']}/{buckets['P0']} = {correct['P0']/buckets['P0']*100:.2f}%",
    "p1_accuracy": f"{correct['P1']}/{buckets['P1']} = {correct['P1']/buckets['P1']*100:.2f}%",
    "p2_accuracy": f"{correct['P2']}/{buckets['P2']} = {correct['P2']/buckets['P2']*100:.2f}%",
    "p3_accuracy": f"{correct['P3']}/{buckets['P3']} = {correct['P3']/buckets['P3']*100:.2f}%",
    "p0_missed_count": len(p0_missed),
    "p1_misjudged_count": len(p1_misjudged),
    "freeze_misjudge_count": len(freeze_misjudge),
    "aml_misjudge_count": len(aml_misjudge),
    "comparison": {
        "v3_10_1_p0": 99.77,
        "v3_10_1_p1": 72.89,
        "round_1_p0": 100.00,
        "round_1_p1": 71.99,
        "round_2_p0": round(correct['P0']/buckets['P0']*100, 2),
        "round_2_p1": round(correct['P1']/buckets['P1']*100, 2),
    },
}
report_path = _ROOT / 'data' / 'v3110_round2_final.json'
report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(f"\n报告: {report_path}")
c.close()
