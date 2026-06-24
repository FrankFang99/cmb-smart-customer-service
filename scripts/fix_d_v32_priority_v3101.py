# -*- coding: utf-8 -*-
"""v3.10.1 fix D v3.2: 升级 44 条 真·P0 query 的 priority (被误标 P1 card_freeze)

D v3.2 评估集 v8.0 重构时, 把"卡被冻/账户异常" 类 query 标成了 P1 card_freeze 业务咨询.
但在生产中, 这类 query 应该 P0 (紧急人工).

不影响训练集 (训练用 v3.5.5 种子集, 与 D v3.2 不交叉).
只动 dedup 版本的 P1 样本, 生成 D_eval_set_v3.2_dedup_v3101.json (新版本).
"""
import json, shutil, sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
_ROOT = Path(r'D:\Learning\AI\面试\AI智能客服')

src_path = _ROOT / 'data' / 'D_eval_set_v3.2_dedup.json'
bak_path = _ROOT / 'data' / 'D_eval_set_v3.2_dedup.bak.json'
new_path = _ROOT / 'data' / 'D_eval_set_v3.2_dedup_v3101.json'

# 备份
if not bak_path.exists():
    shutil.copy(src_path, bak_path)
    print(f'✓ 备份原 dedup eval set -> {bak_path.name}')
else:
    print(f'✓ 原 dedup eval set 备份已存在: {bak_path.name}')

with open(src_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

samples = data.get('samples', []) if isinstance(data, dict) else data
print(f'\n总样本: {len(samples)} 条')

# P0 信号关键词 (出现则升级)
# v3.10.1 v4 进一步收紧: 完全去掉 "被锁/状态不对" 等模糊信号
# 原因: "请问账户被锁住"/"那个账户状态不对" 等礼貌询问 query 实际是 P1 业务咨询
#       礼貌语气 (请问/那个/想问一下) + 模糊信号 → 不该升级 P0
#
# 保留强 P0 信号:
#   - 主动紧急: "紧急"/"被冻结"/"卡冻结了"
#   - 明确异常: "账户异常" (单独)/"卡异常"/"状态异常"
#   - 不能用: "不能用了"/"不能使用"/"突然不能"/"卡封了"
#   - 直接描述: "我的卡被冻"/"我的账户被冻"/"我的卡不能用"
P0_SIGNAL_KEYWORDS = [
    '被冻结', '卡冻结了', '账户冻结了', '卡被冻结', '账户被冻结',
    '卡封了', '卡被封', '账户被封',
    '账户异常,', '账户异常。', '账户异常？', '账户异常?',
    '状态异常', '突然不能', '不能用了', '不能使用',
    '我的卡被冻', '我的账户被冻', '我卡被冻',
    '怎么被冻', '怎么冻了', '怎么冻结',
]

# P0 礼貌询问黑名单: 以这些词开头的 query 即使含 P0_SIGNAL 也不升级
P0_POLITENESS_PREFIXES = ['请问', '那个', '想问一下', '那个请问', '请问我']

# expected_action 升级映射 (因为 D 标的是 P1 card_freeze, 我们升级到 P0 + safety_card_freeze)
PRIORITY_UPGRADE_MAP = {
    'card_freeze': ('P0', 'safety_card_freeze'),
    'card_freeze_with_disambiguation': ('P0', 'safety_card_freeze'),
}

upgraded = 0
upgraded_records = []
for s in samples:
    if not isinstance(s, dict):
        continue
    if s.get('priority') != 'P1':
        continue
    exp = s.get('expected_action', '')
    if exp not in PRIORITY_UPGRADE_MAP:
        continue
    query = s.get('query') or s.get('text') or ''
    if not any(kw in query for kw in P0_SIGNAL_KEYWORDS):
        continue
    # v3.10.1 v4 礼貌询问过滤: "请问/那个/想问一下" 开头的 query 即使含 P0 信号也不升级
    # 因为这些是礼貌询问, 实际是 P1 业务咨询 (问什么是异常/被锁)
    if any(query.startswith(p) for p in P0_POLITENESS_PREFIXES):
        continue
    # 升级
    new_pri, new_exp = PRIORITY_UPGRADE_MAP[exp]
    s['priority'] = new_pri
    s['expected_action'] = new_exp
    s.setdefault('metadata', {})
    s['metadata']['v3101_priority_fix'] = {
        'old_priority': 'P1',
        'old_expected': exp,
        'reason': '真·P0 异常场景, D v3.2 标签错位',
        'signals_matched': [kw for kw in P0_SIGNAL_KEYWORDS if kw in query],
    }
    upgraded += 1
    upgraded_records.append({
        'query': query,
        'new_priority': new_pri,
        'new_expected': new_exp,
    })

print(f'\n升级 P0 样本: {upgraded} 条')

# 写新文件
if isinstance(data, dict):
    data['samples'] = samples
    data['version'] = data.get('version', 'v3.2') + '-v3101-fixed'
    out = data
else:
    out = samples

new_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'\n✓ 新 eval set: {new_path.name}')

# 统计新分布
new_samples = out.get('samples', out) if isinstance(out, dict) else out
from collections import Counter
pri_dist = Counter(s.get('priority') for s in new_samples if isinstance(s, dict))
print(f'\n新分布: {dict(pri_dist)}')
print(f'总样本: {len(new_samples)}')

# 列出升级的样本
print(f'\n=== 升级的 {upgraded} 条样本 (按 query 排序) ===')
for r in sorted(upgraded_records, key=lambda x: x['query']):
    print(f'  [P0/{r["new_expected"]}] {r["query"]}')