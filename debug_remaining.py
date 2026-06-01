"""Debug specific dataset samples"""
import json
import re
from src.components.intent_recognizer import IntentRecognizer
from src.config import settings

recognizer = IntentRecognizer(settings)

# Load dataset
with open('data/evaluation_dataset_v5.1.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

samples = data['samples'][:100]

# Test cases with expected vs actual
test_cases = [
    ("有什么好理财", "sales_wealth_prod"),
    ("最晚什么时候还款", "info_bill_date"),
    ("推荐信用卡", "sales_credit_prod"),
    ("有什么贷款产品", "sales_loan_prod"),
    ("推荐理财产品", "sales_wealth_prod"),
]

print("Direct tests:")
for text, expected in test_cases:
    # Check what rules match
    result = recognizer.recognize(text)
    actual = result.intent.value
    match = "OK" if expected == actual else "FAIL"
    print(f"[{match}] '{text}' -> expected={expected}, actual={actual}")
    print(f"  reasoning: {result.reasoning}")

print("\n\nSearching dataset for specific patterns:")
for i, sample in enumerate(samples):
    q = sample['question']
    expected = sample['intent']
    # Only show sales_loan_prod failures
    if expected == 'sales_loan_prod':
        result = recognizer.recognize(q)
        actual = result.intent.value
        if expected != actual:
            print(f"Index {i}: Q={q.encode('utf-8')}, expected={expected}, actual={actual}")