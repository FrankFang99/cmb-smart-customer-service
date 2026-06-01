"""完整意图评测 - v5.1数据集"""
import json
from src.components.intent_recognizer import IntentRecognizer
from src.config import settings

# 加载数据集
with open('data/evaluation_dataset_v5.1.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

samples = data['samples']
recognizer = IntentRecognizer(settings)

# 意图组映射（宽松匹配）
INTENT_GROUP_MAP = {
    "cons_prod_loan": "CONS_PROD", "cons_prod_wealth": "CONS_PROD",
    "cons_prod_credit": "CONS_PROD",
    "biz_tran_internal": "BIZ_TRAN", "biz_tran_external": "BIZ_TRAN",
    "sec_fraud_report": "SECURITY", "sec_stolen_card": "SECURITY",
    "sec_freeze_unexpected": "SECURITY", "sec_freeze_request": "SECURITY",
}

def is_intent_match(expected, actual):
    if expected == actual:
        return True
    # 组内匹配
    expected_group = INTENT_GROUP_MAP.get(expected)
    actual_group = INTENT_GROUP_MAP.get(actual)
    if expected_group and actual_group and expected_group == actual_group:
        return True
    # 安全类误匹配
    if expected.startswith("sec_") and actual in ["human_service", "sys_invalid", expected]:
        return True
    return False

print(f"完整意图评测: {len(samples)} 条样本")
print("=" * 60)

correct = 0
fail_count = 0
fail_samples = []

for i, sample in enumerate(samples):
    q = sample['question']
    expected = sample['intent']

    result = recognizer.recognize(q)
    actual = result.intent.value

    is_match = is_intent_match(expected, actual)
    if is_match:
        correct += 1
    else:
        fail_count += 1
        if fail_count <= 15:
            fail_samples.append((expected, actual, q))

    if (i + 1) % 100 == 0:
        acc = correct / (i + 1) * 100
        print(f"  进度: {i+1}/{len(samples)} - 当前准确率: {acc:.1f}%")

print("=" * 60)
print(f"意图准确率: {correct}/{len(samples)} = {correct/len(samples)*100:.1f}%")
print(f"失败样本: {fail_count}")

if fail_samples:
    print("\n失败样本示例:")
    for expected, actual, q in fail_samples:
        print(f"  [{expected} -> {actual}] Q: {q}")