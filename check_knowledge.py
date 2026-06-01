"""检查知识库覆盖意图"""
from src.rag.knowledge_base import KNOWLEDGE_BASE

# 数据集v5.0的意图列表（简化）
dataset_intents = [
    "info_acc_balance", "info_acc_detail", "info_bill_amount", "info_bill_date",
    "info_bill_min", "info_bill_point", "info_tran_record", "info_branch", "info_hour",
    "biz_card_loss", "biz_card_activate", "biz_tran_external", "biz_pay_repay",
    "cons_prod_loan", "cons_prod_credit", "cons_fee_tran", "cons_urg_human",
    "sec_fraud_report", "sec_stolen_card",
]

# 知识库中的intent标签
kb_intents = set(item.get("metadata", {}).get("intent", "") for item in KNOWLEDGE_BASE)

print(f"知识库条目数: {len(KNOWLEDGE_BASE)}")
print(f"知识库intent标签数: {len(kb_intents)}")
print()

# 检查关键意图是否覆盖
key_intents = [
    "query_balance", "query_bill", "card_loss", "card_activate",
    "transfer", "password_manage", "consult_rate", "consult_fee",
    "anti_fraud", "theft_report", "marketing_wealth", "marketing_credit",
    "marketing_loan", "human_service", "complaint"
]

print("关键意图覆盖情况:")
for intent in key_intents:
    status = "[OK]" if intent in kb_intents else "[MISS]"
    print(f"  {status} {intent}")

# 统计各类别条目数
categories = {}
for item in KNOWLEDGE_BASE:
    cat = item.get("category", "unknown")
    categories[cat] = categories.get(cat, 0) + 1

print()
print("知识库各类别条目数:")
for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
    print(f"  {cat}: {count}")