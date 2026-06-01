import json
with open('data/evaluation_dataset_v5.1.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 找sys_greeting样本
for s in data['samples']:
    if s['intent'] == 'sys_greeting':
        print(f"intent={s['intent']} Q={s['question']}")