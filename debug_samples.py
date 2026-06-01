"""Debug failing samples"""
import json

with open('data/evaluation_dataset_v5.0.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

samples = data['samples'][:20]

print("Failed samples analysis:")
print("=" * 60)

for i, sample in enumerate(samples):
    q = sample['question']
    expected = sample['intent']

    # Skip if expected matches
    if expected in ['sys_greeting', 'sys_thanks']:
        print(f"{i+1}. EXPECTED={expected:25s} Q={q[:30]}")
        print("   -> This is a single-word intent, likely needs LLM fallback")
        print()