"""Debug recognizer initialization and matching"""
from src.components.intent_recognizer import IntentRecognizer
from src.config import settings

# Try to initialize
recognizer = IntentRecognizer(settings)

# Test patterns
tests = [
    "有什么好理财",
    "推荐理财产品",
    "有什么好产品",
    "转账",
]

for text in tests:
    try:
        result = recognizer.recognize(text)
        print(f"'{text}' -> {result.intent.value} (conf={result.confidence:.2f})")
        print(f"  reasoning: {result.reasoning}")
    except Exception as e:
        print(f"'{text}' -> ERROR: {e}")