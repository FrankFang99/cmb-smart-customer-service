"""A 口径最终报告: P0 红线 4 类 (biz/safety/security/sys) 细分错例分析.

设计目标:
  - 只对 P0 红线覆盖的 4 个业务组出报告 (其他 3 类按设计不属于 P0).
  - 输出 3 张可对外解释的表:
      表 1: 4 类 group 召回率 + fine 召回率 (核心 KPI)
      表 2: 4 类的错误归因 (L1/L2/L3 谁背锅)
      表 3: 4 类的混淆矩阵 (expected → actual 配对)
  - 配 README 友好的人类语言解读, 直接进 RESUME_INTERVIEW_PREP.
"""
import json
from collections import defaultdict, Counter

# === 1. 加载数据 ===
p0 = []
with open('data/p0_badcase_detail.jsonl', encoding='utf-8') as f:
    for line in f:
        d = json.loads(line)
        if d['priority'] == 'P0':
            p0.append(d)

print(f'P0 总数: {len(p0)}')

# A 口径: 只看 4 类 P0 红线
P0_GROUPS = ['biz', 'safety', 'security', 'sys']
p0_in_scope = [d for d in p0 if d['expected_group'] in P0_GROUPS]
print(f'P0 在 4 类范围内: {len(p0_in_scope)} 条')

# === 2. 表 1: 4 类 group 召回率 + fine 召回率 ===
print('\n' + '=' * 80)
print('表 1: P0 红线 4 类召回率 (group 召回 = 大类对, fine 召回 = 细分意图对)')
print('=' * 80)

by_group = defaultdict(lambda: {'total': 0, 'group_correct': 0, 'fine_correct': 0})
for d in p0_in_scope:
    g = d['expected_group']
    by_group[g]['total'] += 1
    if d['group_match']:
        by_group[g]['group_correct'] += 1
    if d['fine_match']:
        by_group[g]['fine_correct'] += 1

print(f'\n{"业务组":12s} {"P0总数":>6s} {"group召回":>10s} {"fine召回":>10s}  状态')
total_g = total_f = total_n = 0
for g in P0_GROUPS:
    s = by_group[g]
    if s['total'] == 0:
        continue
    gr = s['group_correct'] / s['total']
    fr = s['fine_correct'] / s['total']
    if gr < 0.7:
        flag = '🔴 低召回 (重点修复)'
    elif gr < 0.85:
        flag = '🟡 待提升'
    else:
        flag = '🟢 达标'
    print(f'{g:12s} {s["total"]:>6d} {gr*100:>9.2f}% {fr*100:>9.2f}%  {flag}')
    total_g += s['group_correct']
    total_f += s['fine_correct']
    total_n += s['total']
print(f'{"合计":12s} {total_n:>6d} {total_g/total_n*100:>9.2f}% {total_f/total_n*100:>9.2f}%')

# === 3. 表 2: 错误归因 (L1/L2/L3 谁背锅) ===
print('\n' + '=' * 80)
print('表 2: P0 红线 4 类错误归因 (L1 规则 / L2 BERT / L3 兜底)')
print('=' * 80)

attr_map = {
    'L1_rule_group_miss': 'L1规则-大类错',
    'L1_rule_fine_miss': 'L1规则-细分错',
    'L2_bert_group_miss': 'L2 BERT-大类错',
    'L2_bert_fine_miss': 'L2 BERT-细分错',
    'L3_llm_pending_group_miss': 'L3兜底-大类错',
    'L3_llm_pending_fine_miss': 'L3兜底-细分错',
    'correct': '✅正确',
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


for g in P0_GROUPS:
    items = [d for d in p0_in_scope if d['expected_group'] == g]
    if not items:
        continue
    attr_counter = Counter(get_attr(d) for d in items)
    total = sum(attr_counter.values())
    miss = total - attr_counter.get('correct', 0)
    correct = attr_counter.get('correct', 0)
    print(f'\n[{g}] 总 {total} 条, 正确 {correct} ({correct/total*100:.1f}%), 错误 {miss} 条')
    for k, v in attr_counter.most_common():
        if k == 'correct':
            continue
        print(f'  {attr_map.get(k, k):20s} {v:>3d} 条  ({v/total*100:.1f}%)')

# === 4. 表 3: 混淆矩阵 (expected → actual) ===
print('\n' + '=' * 80)
print('表 3: P0 红线 4 类混淆矩阵 (expected → actual 配对 Top 10)')
print('=' * 80)

# group 错配
print('\n--- 4.1 group 级错配 (大类判错) ---')
g_conf = Counter()
for d in p0_in_scope:
    if not d['group_match']:
        g_conf[(d['expected_group'], d['actual_group'])] += 1
for (exp, act), n in g_conf.most_common(10):
    print(f'  {exp:10s} → {act:10s}  {n:>3d} 条')

# fine 错配 (group 对, 细分错)
print('\n--- 4.2 fine 级错配 (大类对, 细分错) Top 10 ---')
f_conf = Counter()
for d in p0_in_scope:
    if d['group_match'] and not d['fine_match']:
        f_conf[(d['expected_intent'], d['actual_intent'])] += 1
for (exp, act), n in f_conf.most_common(10):
    print(f'  {exp:35s} → {act:35s}  {n:>3d} 条')

# === 5. 4 类各自最严重的细分错 Top 3 ===
print('\n' + '=' * 80)
print('表 4: 4 类各自最严重的细分错例 (按组 Top 3, 带样本展示)')
print('=' * 80)

for g in P0_GROUPS:
    items = [d for d in p0_in_scope if d['expected_group'] == g]
    g_miss = Counter()
    f_miss = Counter()
    for d in items:
        if not d['group_match']:
            g_miss[(d['expected_intent'], d['actual_intent'])] += 1
        elif not d['fine_match']:
            f_miss[(d['expected_intent'], d['actual_intent'])] += 1
    print(f'\n[{g}] group 错配 {sum(g_miss.values())} 条, fine 错配 {sum(f_miss.values())} 条')
    print(f'  Top 3 group 错配:')
    for (exp, act), n in g_miss.most_common(3):
        print(f'    {exp:30s} → {act:30s}  {n} 条')
    print(f'  Top 3 fine 错配:')
    for (exp, act), n in f_miss.most_common(3):
        print(f'    {exp:30s} → {act:30s}  {n} 条')

# === 6. 4 类问题样本 (供简历/PPT 引用, 各取 2 条典型) ===
print('\n' + '=' * 80)
print('表 5: 4 类典型问题样本 (供面试引用)')
print('=' * 80)
for g in P0_GROUPS:
    items = [d for d in p0_in_scope if d['expected_group'] == g and not d['fine_match']]
    print(f'\n[{g}] 取 2 条典型错例:')
    for d in items[:2]:
        print(f"  Q: {d['question']}")
        print(f"    期望: {d['expected_intent']}  →  实际: {d['actual_intent']}")
        print(f"    路由层: {d['cascade_source']}  置信度: {d['cascade_confidence']}")
        print()
