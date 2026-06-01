import json
from src.eval.eval_runner import MockCustomerServiceAgent

data = json.load(open('data/evaluation_dataset_v3.0.json', 'r', encoding='utf-8'))
agent = MockCustomerServiceAgent([])

correct = 0
total = 0
wrong_samples = []

for s in data['samples']:
    result = agent.process(s['question'], {})
    total += 1
    if result['intent'] == s['intent']:
        correct += 1
    else:
        wrong_samples.append({
            'id': s['id'],
            'expected': s['intent'],
            'actual': result['intent'],
            'question': s['question'][:50]
        })

print(f"Accuracy: {correct}/{total} = {correct/total*100:.1f}%")
print(f"\nTop wrong intents:")
wrong_intents = {}
for w in wrong_samples:
    key = w['expected']
    wrong_intents[key] = wrong_intents.get(key, 0) + 1
for k, v in sorted(wrong_intents.items(), key=lambda x: x[1], reverse=True)[:10]:
    print(f"  {k}: {v}")