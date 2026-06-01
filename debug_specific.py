"""Debug remaining failures"""
import json
from src.components.intent_recognizer import IntentRecognizer
from src.config import settings

recognizer = IntentRecognizer(settings)

# Load dataset
with open('data/evaluation_dataset_v5.1.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

samples = data['samples'][:100]

# Specific test cases
test_cases = [
    ("有什么好理财", "sales_wealth_prod"),
    ("你好", "sys_greeting"),
    ("查一下交易明细", "info_tran_record"),
    ("有什么贷款产品", "sales_loan_prod"),
    ("最晚什么时候还款", "info_bill_date"),
    ("账户异常冻结", "sec_freeze_unexpected"),
    ("推荐信用卡", "sales_credit_prod"),
    ("转账手续费多少", "cons_fee_tran"),
    ("有什么好产品", "sales_loan_prod"),
    ("在吗", "sys_greeting"),
]

print("Testing specific cases:")
for text, expected in test_cases:
    result = recognizer.recognize(text)
    actual = result.intent.value
    match = "OK" if expected == actual else "FAIL"
    print(f"[{match}] {text} -> expected={expected}, actual={actual}")