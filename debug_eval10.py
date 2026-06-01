"""Debug quick_eval100 step by step"""
import json
from src.components.intent_recognizer import IntentRecognizer
from src.config import settings

recognizer = IntentRecognizer(settings)

# 加载数据集
with open('data/evaluation_dataset_v5.1.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

samples = data['samples'][:10]

print("First 10 samples:")
for i, sample in enumerate(samples[:10]):
    q = sample['question']
    expected = sample['intent']

    result = recognizer.recognize(q)
    actual = result.intent.value

    match = "OK" if expected == actual else "FAIL"
    print(f"{i+1}. [{match}] {expected} -> {actual} | Q={q}")