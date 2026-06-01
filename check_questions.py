"""Check actual question strings"""
import json

with open('data/evaluation_dataset_v5.1.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Check specific samples
for idx in [7, 8, 14]:  # 0-indexed
    s = data['samples'][idx]
    q = s['question']
    print(f"Index {idx}: intent={s['intent']}")
    print(f"  Question: '{q}'")
    print(f"  Bytes: {q.encode('utf-8')}")
    print(f"  Unicode: {[hex(ord(c)) for c in q]}")
    print()