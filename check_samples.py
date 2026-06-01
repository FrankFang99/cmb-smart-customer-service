import json

with open('data/evaluation_dataset_v5.0.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 检查前20个样本
print("First 20 samples in dataset:")
print("=" * 60)
for i, s in enumerate(data['samples'][:20]):
    print(f"{i+1:2d}. {s['intent']:30s} Q={s['question'][:40]}")