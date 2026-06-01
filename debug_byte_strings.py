"""Debug specific strings byte by byte"""
import json

with open('data/evaluation_dataset_v5.1.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Find specific samples
for i, s in enumerate(data['samples'][:100]):
    q = s['question']
    intent = s['intent']

    # Check for "推荐" related
    if '信用卡' in q or '贷款' in q or '理财' in q:
        print(f"Index {i}: intent={intent}")
        print(f"  Question: {q}")
        print(f"  Bytes: {q.encode('utf-8').hex()}")
        print(f"  Unicode chars: {[hex(ord(c)) for c in q]}")
        print()