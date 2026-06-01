"""Debug specific failures in dataset"""
import json
from src.components.intent_recognizer import IntentRecognizer
from src.config import settings

recognizer = IntentRecognizer(settings)

# Load dataset
with open('data/evaluation_dataset_v5.1.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

samples = data['samples'][:100]

# Find specific failing samples
fail_cases = [
    ("sales_wealth_prod", "有什么好理财"),
    ("sys_greeting", "在吗"),
    ("sales_loan_prod", "有什么贷款产品"),
    ("info_bill_date", "最晚什么时候还款"),
    ("sales_credit_prod", "推荐信用卡"),
    ("cons_fee_tran", "转账手续费多少"),
    ("sec_freeze_unexpected", "账户异常冻结"),
]

print("Testing against dataset samples:")
for expected, text in fail_cases:
    result = recognizer.recognize(text)
    actual = result.intent.value
    match = "OK" if expected == actual else "FAIL"
    print(f"[{match}] '{text}' -> expected={expected}, actual={actual}")

print("\n\nSearching for actual dataset samples:")
for i, sample in enumerate(samples):
    q = sample['question']
    expected = sample['intent']
    if expected == 'sys_greeting':
        result = recognizer.recognize(q)
        actual = result.intent.value
        if expected != actual:
            print(f"MISMATCH: index={i}, Q={q}, expected={expected}, actual={actual}")