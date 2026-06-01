from src.components.intent_recognizer import IntentRecognizer
from src.config import settings

recognizer = IntentRecognizer(settings)

# Check sales_rules content
print("Sales rules (first 3):")
for i, (pattern, intent) in enumerate(recognizer._sales_rules[:3]):
    print(f"  {i}: {intent} = {pattern}")

# Check if '有什么好理财' matches
text = "有什么好理财"
result = recognizer.recognize(text)
print()
print(f'Test "有什么好理财":')
print(f"  Result: {result.intent.value}")
print(f"  Reasoning: {result.reasoning}")