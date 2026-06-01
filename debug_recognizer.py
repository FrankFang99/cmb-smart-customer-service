"""Debug specific intent recognition"""
from src.components.intent_recognizer import IntentRecognizer
from src.config import settings

recognizer = IntentRecognizer(settings)

test_cases = [
    "交易记录",
    "跨行转账",
    "我被骗了",
    "贷款利率多少",
    "你好",
    "谢谢",
]

print("Intent Recognizer Debug:")
print("=" * 60)
for text in test_cases:
    result = recognizer.recognize(text)
    print(f"{text:30s} -> {result.intent.value:30s} (conf={result.confidence:.2f})")