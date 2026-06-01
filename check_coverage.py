import json

# 加载数据集
with open('data/evaluation_dataset_v4.0.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"数据集: {data['dataset_version']}")
print(f"总样本数: {data['total_samples']}")
print(f"意图类型数: {data['intent_count']}")
print()

# 统计每个意图的样本数和问法
intent_samples = {}
for s in data['samples']:
    intent = s['intent']
    if intent not in intent_samples:
        intent_samples[intent] = []
    intent_samples[intent].append(s['question'])

print("意图覆盖分析:")
print("=" * 60)

# 按类别分组
categories = {}
for intent, questions in intent_samples.items():
    cat = intent.split('_')[0].upper()
    if cat not in categories:
        categories[cat] = []
    categories[cat].append((intent, len(questions), questions[0]))

for cat in ['INFO', 'BIZ', 'CONS', 'SEC', 'SALES', 'SYS']:
    if cat not in categories:
        continue
    print(f"\n[{cat}]({len(categories[cat])}种意图)")
    for intent, count, sample in sorted(categories[cat], key=lambda x: -x[1]):
        status = "[OK]" if count >= 10 else "[LOW]" if count >= 5 else "[FEW]"
        print(f"  {status} {intent:30s}: {count}条 | {sample[:25]}...")

print()
print("=" * 60)
print(f"总计: {data['total_samples']}条样本, {data['intent_count']}种意图")