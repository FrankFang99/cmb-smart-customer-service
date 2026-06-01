"""完整评测 - v5.1真实数据集"""
import json
from src.agent.customer_service_agent import CustomerServiceAgent
from src.config import settings

# 加载数据集
with open('data/evaluation_dataset_v5.1.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

samples = data['samples']
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

print(f"完整评测: {len(samples)} 条样本")
print("=" * 60)

correct = 0
fail_count = 0
fail_samples = []

for i, sample in enumerate(samples):
    q = sample['question']
    expected = sample['intent']

    result = agent.chat(q)
    actual = result['intent']

    is_match = is_intent_match(expected, actual)
    if is_match:
        correct += 1
    else:
        fail_count += 1
        if fail_count <= 20:  # 只记录前20个失败
            fail_samples.append((expected, actual, q))

    if (i + 1) % 100 == 0:
        print(f"  进度: {i+1}/{len(samples)}")

print("=" * 60)
print(f"意图准确率: {correct}/{len(samples)} = {correct/len(samples)*100:.1f}%")
print(f"失败样本: {fail_count}")

if fail_samples:
    print("\n失败样本示例:")
    for expected, actual, q in fail_samples[:10]:
        print(f"  [{expected} -> {actual}] Q: {q}")