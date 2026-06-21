"""P0 各 group 的样本细节"""
import json
from collections import Counter

groups_p0 = Counter()
groups_all = Counter()
with open('data/p0_badcase_detail.jsonl', encoding='utf-8') as f:
    for line in f:
        d = json.loads(line)
        if d['priority'] == 'P0':
            groups_p0[d['expected_group']] += 1
        groups_all[d['expected_group']] += 1

print('P0 各业务组样本数:', dict(groups_p0))
print('全量 1500 条各业务组样本数:', dict(groups_all))

# biz→security 这 19 条样本
print('\n=== biz→security 这 19 条样本 (P0) ===')
biz_sec = []
with open('data/p0_badcase_detail.jsonl', encoding='utf-8') as f:
    for line in f:
        d = json.loads(line)
        if (d['priority'] == 'P0' and d['expected_group'] == 'biz'
                and d['actual_group'] == 'security'):
            biz_sec.append(d)

for d in biz_sec[:10]:
    print(f"  Q: {d['question']}")
    print(f"    exp: {d['expected_intent']:30s} -> act: {d['actual_intent']:30s}")
    print(f"    source={d['cascade_source']} conf={d['cascade_confidence']}")
    print()

# security 错 (含 23 条 security→safety + 17 条 security→sys)
print('=== security→safety 错配 (前 6 条) ===')
sec_saf = []
with open('data/p0_badcase_detail.jsonl', encoding='utf-8') as f:
    for line in f:
        d = json.loads(line)
        if (d['priority'] == 'P0' and d['expected_group'] == 'security'
                and d['actual_group'] == 'safety'):
            sec_saf.append(d)
for d in sec_saf[:6]:
    print(f"  Q: {d['question']}")
    print(f"    exp: {d['expected_intent']:30s} -> act: {d['actual_intent']:30s}")

print('\n=== security→sys 错配 (前 6 条) ===')
sec_sys = []
with open('data/p0_badcase_detail.jsonl', encoding='utf-8') as f:
    for line in f:
        d = json.loads(line)
        if (d['priority'] == 'P0' and d['expected_group'] == 'security'
                and d['actual_group'] == 'sys'):
            sec_sys.append(d)
for d in sec_sys[:6]:
    print(f"  Q: {d['question']}")
    print(f"    exp: {d['expected_intent']:30s} -> act: {d['actual_intent']:30s}")