from src.components.intent_recognizer import IntentRecognizer
from src.config import settings

recognizer = IntentRecognizer(settings)

test_questions = [
    '我卡里还有多少钱',
    '信用卡欠了20万还不上了',
    '卡丢了怎么办',
    '转账要手续费吗',
    '转人工',
    '被骗了怎么办',
    '你好',
]

print("测试意图识别器（含LLM兜底）")
print("=" * 60)

for q in test_questions:
    result = recognizer.recognize(q)
    print(f"Q: {q}")
    print(f"  Intent: {result.intent.value}")
    print(f"  Confidence: {result.confidence:.2f}")
    print(f"  Transfer: {result.should_transfer}")
    print(f"  Reason: {result.reasoning}")
    print()