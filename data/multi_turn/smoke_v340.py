"""5 sample smoke test for v3.4.0"""
import sys
sys.path.insert(0, r'D:\Learning\AI\面试\AI智能客服')
from scripts.eval_v340_real_llm import evaluate_sample, create_e2e_pipeline, IntentRecognizer
import json
with open(r'D:\Learning\AI\面试\AI智能客服\data\evaluation_dataset_v5.1.json', encoding='utf-8') as f:
    data = json.load(f)
pipeline = create_e2e_pipeline(k=3)
ir = IntentRecognizer()
for s in data['samples'][:5]:
    r = evaluate_sample(pipeline, ir, s)
    expected = r['expected_intent']
    actual = r.get('actual_intent', 'N/A')
    match = r['intent_match']
    p0 = r.get('p0_recall')
    elapsed = r['elapsed_ms']
    print(f'{s["id"]}: exp={expected:25s} act={actual:25s} match={match} p0={p0} {elapsed}ms')
