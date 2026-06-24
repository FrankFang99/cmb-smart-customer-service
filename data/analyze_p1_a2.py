"""A2 P1 analysis: cluster the 90 P1 -> transfer_human wrong cases.
Goal: find which P0 patch patterns are misfiring on P1 queries.
"""
import sqlite3, json, re
from collections import Counter, defaultdict
from pathlib import Path

DB = r"D:\Learning\AI\面试\AI智能客服\data\observability_v3101_full.db"
OUT = Path(r"D:\Learning\AI\面试\AI智能客服\data\p1_a2_analysis.json")

c = sqlite3.connect(DB)
cur = c.cursor()

# 1. Get all 90 P1 -> transfer_human cases
cur.execute("""
SELECT trace_id, user_input, final_intent, intent_top1, expected_action, p0_triggered
FROM traces
WHERE priority='P1' AND final_action='transfer_human'
ORDER BY expected_action, user_input
""")
wrong_rows = cur.fetchall()
print(f"P1 wrong (transfer_human): {len(wrong_rows)}")

# 2. Cluster by expected_action (target intent) and detect query type keywords
def classify_query_type(q, expected):
    """Heuristic: group P1 wrong cases by query pattern type."""
    ql = q.lower()
    # Transfer-related (high risk for biz_transfer_large误伤)
    if any(k in q for k in ["转账", "汇款", "转给", "转出", "转入", "给公司", "转个", "转 50", "转 100"]):
        return "transfer_业务咨询"
    # Loan-related
    if any(k in q for k in ["贷款", "借钱", "借呗", "借了", "信用贷", "消费贷"]):
        return "loan_业务咨询"
    # Repay-related
    if any(k in q for k in ["还款", "还贷款", "还信用卡", "提前还", "怎么还", "如何还", "主动还", "还清"]):
        return "repay_业务咨询"
    # Fund/Wealth-related
    if any(k in q for k in ["理财", "基金", "余额宝", "买入", "收益", "净值", "亏了", "保本"]):
        return "wealth_业务咨询"
    # Deposit-related
    if any(k in q for k in ["存款", "大额存单", "定期", "活期", "存钱"]):
        return "deposit_业务咨询"
    # Card-related
    if any(k in q for k in ["信用卡", "银行卡", "额度", "账单", "开卡", "补卡", "激活卡"]):
        return "card_业务咨询"
    # Password / login
    if any(k in q for k in ["密码", "登录", "忘记密码", "锁定", "解锁"]):
        return "password_业务咨询"
    # Cross-border
    if any(k in q for k in ["境外", "国外", "外汇", "汇率", "美元", "跨境"]):
        return "fx_业务咨询"
    # How-to (操作类 — v364 已删 怎么办/怎么操作，但其他 怎么+动词 可能误伤)
    if any(k in q for k in ["怎么办", "怎么操作", "怎么用", "怎么弄", "如何操作", "怎么开通", "怎么开"]):
        return "how_to_操作咨询"
    # Fee / charge
    if any(k in q for k in ["手续费", "年费", "管理费", "多少钱"]):
        return "fee_业务咨询"
    return "other"

# 3. Apply cluster
clusters = defaultdict(list)
for row in wrong_rows:
    trace_id, query, final_intent, intent_top1, expected, p0_triggered = row
    qtype = classify_query_type(query, expected)
    clusters[qtype].append({
        "query": query,
        "final_intent": final_intent,
        "intent_top1": intent_top1,
        "expected_action": expected,
        "p0_triggered": bool(p0_triggered),
    })

# 4. Summary
summary = []
print()
print("=" * 70)
print("[A2 P1 wrong cluster]")
print("=" * 70)
for qtype in sorted(clusters.keys(), key=lambda k: -len(clusters[k])):
    items = clusters[qtype]
    summary.append({"qtype": qtype, "n": len(items)})
    print(f"\n--- {qtype} ({len(items)}) ---")
    for it in items[:8]:
        print(f"  Q: {it['query'][:60]}")
        print(f"     final={it['final_intent']} | top1={it['intent_top1']} | exp={it['expected_action']}")

# 5. Expected action distribution
exp_dist = Counter(r[4] for r in wrong_rows)
print()
print("=" * 70)
print("[P1 wrong by expected_action — 哪些 intent 被误伤了]")
print("=" * 70)
for k, n in exp_dist.most_common(15):
    print(f"  {k}: {n}")

# 6. P0_triggered rate overall
p0t_count = sum(1 for r in wrong_rows if r[5])
print(f"\nP0 triggered (真·P0 patch 命中): {p0t_count}/{len(wrong_rows)} = {p0t_count/len(wrong_rows)*100:.1f}%")

# 7. Save JSON
out_data = {
    "version": "v3.10.1-p1-a2-analysis",
    "source_db": "observability_v3101_full.db",
    "source_report": "observable_v3101_full_report.json",
    "p1_wrong_total": len(wrong_rows),
    "p0_triggered_count": p0t_count,
    "p0_triggered_rate": round(p0t_count/len(wrong_rows), 4) if wrong_rows else 0,
    "cluster_summary": summary,
    "cluster_total_count": sum(len(v) for v in clusters.values()),
    "expected_action_top": exp_dist.most_common(20),
    "clusters": {k: v for k, v in clusters.items()},
}
OUT.write_text(json.dumps(out_data, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n✓ A2 分析写入: {OUT}")

c.close()