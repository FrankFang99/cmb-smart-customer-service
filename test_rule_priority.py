"""测试规则优先级修复"""
from src.components.intent_recognizer import IntentRecognizer
from src.config import settings

recognizer = IntentRecognizer(settings)

test_cases = [
    ("我信用卡欠了20万还不上了", "应该是info_bill_amount"),
    ("账单金额是多少", "应该是info_bill_amount"),
    ("我欠了银行3万", "应该是info_bill_amount"),
    ("信用卡额度多少", "应该是cons_prod_credit"),
    ("我的信用卡年费多少", "应该是cons_prod_credit"),
    ("想了解信用卡申请流程", "应该是cons_prod_credit"),
    ("我卡里欠了2万", "应该是info_bill_amount"),
]

print("测试规则优先级修复:")
print("=" * 60)
for text, expected in test_cases:
    result = recognizer.recognize(text)
    status = "[OK]" if result.intent.value in expected else "[FAIL]"
    print(f"{status} {text[:30]:30s} -> {result.intent.value:25s} ({expected})")