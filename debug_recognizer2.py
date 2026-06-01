"""Debug IntentRecognizer"""
from src.components.intent_recognizer import IntentRecognizer
from src.config import settings

recognizer = IntentRecognizer(settings)

print("Rule groups:", [g[0] for g in recognizer._rule_groups])
print()

# Test cases
test_cases = ["你好", "您好", "在吗", "要还多少钱", "推荐信用卡", "推荐贷款"]

for text in test_cases:
    result = recognizer.recognize(text)
    print(f"'{text}' -> intent={result.intent.value}, conf={result.confidence:.2f}")
    print(f"  reasoning: {result.reasoning}")