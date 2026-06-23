"""Round 2: 累积负例库"""
import json
from pathlib import Path

_ROOT = Path(r'D:\Learning\AI\面试\AI智能客服')
import sys
sys.path.insert(0, str(_ROOT))

from src.eval.badcase_patches_v311_r2 import get_v311_r2_negative_examples

negs = get_v311_r2_negative_examples()
out_path = _ROOT / 'data' / 'negative_candidates_v311_r2.jsonl'
with open(out_path, 'w', encoding='utf-8') as f:
    for nc in negs:
        nc['source'] = 'p1_boundary_cumulative_r1+r2'
        f.write(json.dumps(nc, ensure_ascii=False) + '\n')

print(f"Round 2 累积负例库: {len(negs)} 条 → {out_path}")
print(f"  R1 baseline: {sum(1 for n in negs if n.get('round_added')=='r1')}")
print(f"  R2 regression: {sum(1 for n in negs if n.get('round_added')=='r2')}")
