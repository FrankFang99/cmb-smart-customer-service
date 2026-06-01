import json

with open('data/evaluation_dataset_v3.0.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 统计意图分布
intent_counts = {}
for s in data['samples']:
    intent = s.get('expected_intent', s.get('intent', 'unknown'))
    intent_counts[intent] = intent_counts.get(intent, 0) + 1

print(f"总样本数: {len(data['samples'])}")
print(f"意图类型数: {len(intent_counts)}")
print()
print("意图分布 (Top 30):")
for intent, count in sorted(intent_counts.items(), key=lambda x: -x[1])[:30]:
    print(f"  {intent:30s}: {count}")

print()
print("所有意图类型:")
for intent in sorted(intent_counts.keys()):
    print(f"  - {intent}")