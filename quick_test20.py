"""快速评测20条样本"""
import json
from src.agent.customer_service_agent import CustomerServiceAgent
from src.config import settings

# 加载数据集
with open('data/evaluation_dataset_v5.0.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

samples = data['samples'][:20]
agent = CustomerServiceAgent(settings)

# 意图组映射
INTENT_GROUP_MAP = {
    "cons_prod_loan": "CONS_PROD", "cons_prod_wealth": "CONS_PROD",
    "cons_prod_credit": "CONS_PROD",
    "biz_tran_internal": "BIZ_TRAN", "biz_tran_external": "BIZ_TRAN",
    "sec_fraud_report": "SECURITY", "sec_stolen_card": "SECURITY",
}

def is_intent_match(expected, actual):
    if expected == actual:
        return True
    expected_group = INTENT_GROUP_MAP.get(expected)
    actual_group = INTENT_GROUP_MAP.get(actual)
    if expected_group and actual_group and expected_group == actual_group:
        return True
    if expected.startswith("sec_") and actual in ["human_service", expected]:
        return True
    if expected.startswith("cons_urg") and actual in ["sys_invalid", "human_service", expected]:
        return True
    return False

print(f"快速评测20条样本:")
print("=" * 60)

correct = 0
for i, sample in enumerate(samples):
    q = sample['question']
    expected = sample['intent']

    result = agent.chat(q)
    actual = result['intent']

    is_match = is_intent_match(expected, actual)
    if is_match:
        correct += 1

    status = "[OK]" if is_match else "[FAIL]"
    print(f"{i+1:2d}. {status} {expected[:25]:25s} -> {actual[:25]:25s}")

print("=" * 60)
print(f"意图准确率: {correct}/{len(samples)} = {correct/len(samples)*100:.0f}%")