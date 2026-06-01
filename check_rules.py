"""检查意图识别器规则覆盖"""
import json

# 加载数据集
with open('data/evaluation_dataset_v4.0.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 获取数据集里所有意图
dataset_intents = set(s['intent'] for s in data['samples'])

# 读取 intent_recognizer.py 中的规则
import re
with open('src/components/intent_recognizer.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 提取所有规则对应的意图 - 格式: (r"pattern", "intent")
rule_intents = set()
# 匹配 (r"...", "intent") 格式
for match in re.finditer(r'\(r"[^"]+".*?,\s*"([a-z_]+)"\)', content):
    intent = match.group(1)
    rule_intents.add(intent)

print(f"数据集意图数: {len(dataset_intents)}")
print(f"规则覆盖意图数: {len(rule_intents)}")
print()

# 找出未覆盖的意图
uncovered = dataset_intents - rule_intents
print(f"未覆盖意图数: {len(uncovered)}")
if uncovered:
    print("\n未覆盖的意图:")
    for intent in sorted(uncovered):
        print(f"  - {intent}")

# 覆盖情况
covered = dataset_intents & rule_intents
print(f"\n已覆盖意图数: {len(covered)}")
print(f"覆盖率: {len(covered)/len(dataset_intents)*100:.1f}%")