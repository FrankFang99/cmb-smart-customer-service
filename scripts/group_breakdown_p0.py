"""P0-only 7 类 group 召回率 + fine 召回率分析"""
import json
from collections import defaultdict

p0 = []
with open('data/p0_badcase_detail.jsonl', encoding='utf-8') as f:
    for line in f:
        d = json.loads(line)
        if d['priority'] == 'P0':
            p0.append(d)

print(f'P0 总数: {len(p0)}')

# 按 group 聚合 (按 expected_group)
by_group = defaultdict(lambda: {'total': 0, 'group_correct': 0, 'fine_correct': 0})
for d in p0:
    g = d['expected_group']
    by_group[g]['total'] += 1
    if d['group_match']:
        by_group[g]['group_correct'] += 1
    if d['fine_match']:
        by_group[g]['fine_correct'] += 1

print(f'\n=== P0 7 类召回率 ===')
print(f'{"业务组":12s} {"P0总数":>6s} {"group召回":>10s} {"fine召回":>10s}  状态')
total_g = total_f = total_n = 0
rows = []
for g, s in by_group.items():
    gr = s['group_correct'] / s['total']
    fr = s['fine_correct'] / s['total']
    flag = '🔴 低召回' if gr < 0.7 else '🟡 待提升' if gr < 0.85 else '🟢 达标'
    rows.append((g, s['total'], gr, fr, flag))
    total_g += s['group_correct']
    total_f += s['fine_correct']
    total_n += s['total']

rows.sort(key=lambda x: -x[2])  # 按 group 召回降序
for g, n, gr, fr, flag in rows:
    print(f'{g:12s} {n:>6d} {gr*100:>9.2f}% {fr*100:>9.2f}%  {flag}')
print(f'{"合计":12s} {total_n:>6d} {total_g/total_n*100:>9.2f}% {total_f/total_n*100:>9.2f}%')

# 错误归因按 group
print('\n=== P0 各组错误归因 ===')
attr_by_group = defaultdict(lambda: defaultdict(int))
attr_map = {
    'L1_rule_group_miss': 'L1规则-大类错',
    'L1_rule_fine_miss': 'L1规则-细分错',
    'L2_bert_group_miss': 'L2 BERT-大类错',
    'L2_bert_fine_miss': 'L2 BERT-细分错',
    'L3_llm_pending_group_miss': 'L3兜底-大类错',
    'L3_llm_pending_fine_miss': 'L3兜底-细分错',
    'correct': '正确',
}


def get_attr(d):
    if d['group_match'] and d['fine_match']:
        return 'correct'
    if not d['group_match']:
        if d['cascade_source'] == 'L1_rule':
            return 'L1_rule_group_miss'
        if d['cascade_source'] == 'L2_bert':
            return 'L2_bert_group_miss'
        if d['use_llm_fallback']:
            return 'L3_llm_pending_group_miss'
        return 'group_miss_other'
    if d['cascade_source'] == 'L1_rule':
        return 'L1_rule_fine_miss'
    if d['cascade_source'] == 'L2_bert':
        return 'L2_bert_fine_miss'
    if d['use_llm_fallback']:
        return 'L3_llm_pending_fine_miss'
    return 'fine_miss_other'


for d in p0:
    a = get_attr(d)
    attr_by_group[d['expected_group']][a] += 1

for g in sorted(attr_by_group.keys()):
    s = attr_by_group[g]
    total = sum(s.values())
    if total == 0:
        continue
    miss = total - s.get('correct', 0)
    print(f'\n[{g}] 总 {total} 条, 错误 {miss} 条')
    for k, v in sorted(s.items(), key=lambda x: -x[1]):
        if k == 'correct':
            continue
        print(f'  {attr_map.get(k, k):14s} {v:>3d} 条  ({v/total*100:.1f}%)')

# 低召回组的混淆对
print('\n=== 低召回 group 的主要混淆对 (expected→actual) ===')
low_groups = [g for g, s in by_group.items() if s['group_correct'] / s['total'] < 0.7]
confusion = defaultdict(int)
for d in p0:
    if not d['group_match'] and d['expected_group'] in low_groups:
        confusion[(d['expected_group'], d['actual_group'])] += 1

for (exp, act), n in sorted(confusion.items(), key=lambda x: -x[1]):
    print(f'  {exp:10s} → {act:10s}  {n} 条')

# 低召回组的 fine 错混淆对 (取 group 对 / fine 错 中贡献最多的)
print('\n=== 低召回 group 的 fine 错混淆对 (group 对 / fine 错) ===')
fine_conf = defaultdict(int)
for d in p0:
    if d['group_match'] and not d['fine_match'] and d['expected_group'] in low_groups:
        fine_conf[(d['expected_intent'], d['actual_intent'])] += 1

for (exp, act), n in sorted(fine_conf.items(), key=lambda x: -x[1])[:15]:
    print(f'  {exp:35s} → {act:35s}  {n} 条')