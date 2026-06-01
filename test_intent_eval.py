from src.components.intent_recognizer import IntentRecognizer
from src.config import settings
import json

recognizer = IntentRecognizer(settings)

# 加载数据集
with open("data/evaluation_dataset_v3.0.json", "r", encoding="utf-8") as f:
    data = json.load(f)

samples = data["samples"][:20]

print("测试意图识别器（规则+LLM兜底）")
print("=" * 60)

correct = 0
for i, sample in enumerate(samples):
    q = sample["question"]
    expected = sample["intent"]
    
    result = recognizer.recognize(q)
    actual = result.intent.value
    
    is_match = expected == actual
    if is_match:
        correct += 1
    
    status = "[OK]" if is_match else "[FAIL]"
    print(f"{i+1:2d}. {status} expected={expected[:25]:25s} actual={actual[:25]:25s}")
    if not is_match:
        print(f"       Reason: {result.reasoning}")

print("=" * 60)
print(f"意图识别准确率: {correct}/{len(samples)} = {correct/len(samples)*100:.1f}%")