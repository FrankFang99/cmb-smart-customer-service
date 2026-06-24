"""A2 P1 detailed analysis: cluster by which P0 patch (final_intent) is misfiring.
Output patch 收紧候选.
"""
import sqlite3, json, re
from collections import Counter, defaultdict
from pathlib import Path

DB = r"D:\Learning\AI\面试\AI智能客服\data\observability_v3101_full.db"
A2_PATH = Path(r"D:\Learning\AI\面试\AI智能客服\data\p1_a2_analysis.json")
a2 = json.loads(A2_PATH.read_text(encoding="utf-8"))

c = sqlite3.connect(DB)
cur = c.cursor()

# 1. Group by final_intent (which P0 patch 误伤)
print("=" * 70)
print("[A2: 按 P0 patch (final_intent) 分组 — 哪些 patch 误伤最多]")
print("=" * 70)

patch_groups = defaultdict(list)
for qtype, items in a2["clusters"].items():
    for it in items:
        patch_groups[it["final_intent"] or "(none)"].append({
            "query": it["query"],
            "expected": it["expected_action"],
            "qtype": qtype,
        })

patch_summary = []
for patch, items in sorted(patch_groups.items(), key=lambda x: -len(x[1])):
    patch_summary.append({"patch": patch, "wrong_count": len(items)})
    print(f"\n--- P0 patch: {patch} (误伤 {len(items)}) ---")
    # Top 3 expected_action
    exp_top = Counter(it["expected"] for it in items).most_common(3)
    print(f"  被误伤的 intent: {exp_top}")
    for it in items[:10]:
        print(f"  Q: {it['query'][:60]}")
        print(f"     -> 期望: {it['expected']} | query_type: {it['qtype']}")

# 2. 识别关键 patch + 收紧建议
print()
print("=" * 70)
print("[Patch 收紧建议]")
print("=" * 70)

suggestions = []

# 2.1 safety_card_freeze 误伤 — 卡冻结了/P0 miss 但 P1 用户问的是"怎么解冻"
# 修复方向: 加 "怎么办/怎么解冻/为什么被冻" 等疑问型短句不被当 P0
if "safety_card_freeze" in patch_groups:
    n = len(patch_groups["safety_card_freeze"])
    suggestions.append({
        "patch": "safety_card_freeze",
        "wrong_count": n,
        "root_cause": "P0 patch 把所有 '卡被冻/卡冻结/卡不能用了' 都路由转人工, 但 P1 用户实际想 '怎么解冻/为什么被冻'",
        "fix_direction": "收紧: 在 safety_card_freeze patch 里加 '疑问型信号豁免' — 如果 query 含 '怎么/为什么/咋办/怎么办/如何', 降级到 P1 业务咨询",
        "priority": "P0",
    })

# 2.2 biz_transfer_large 误伤 — "怎么办/怎么操作" 宽匹配仍有问题
# 已知 v3.10.1 已删 怎么办/怎么操作, 但仍有 "基金定投怎么操作" / "贷款怎么办" 等触发
if "biz_transfer_large" in patch_groups:
    biz = patch_groups["biz_transfer_large"]
    n = len(biz)
    triggers = [it["query"] for it in biz]
    suggestions.append({
        "patch": "biz_transfer_large",
        "wrong_count": n,
        "root_cause": "P0 patch '我要转 X 万' / 'X 万给公司' 仍把部分业务咨询 query 误吞 (例如 '基金定投怎么操作'/'贷款怎么办'/'理财怎么办')",
        "fix_direction": "收紧: 当 final_intent=biz_transfer_large 但 expected ≠ biz_transfer_large, 在 patch 里加白名单 (intent_top1 = biz_loan_repay / consult_loan_credit / consult_wealth_fund 时降级到 P1)",
        "priority": "P0",
    })

# 2.3 l0_redline 误伤 — "大额存单" / "卡冻结了" 等无金额/无威胁关键词也被红线触发
if "l0_redline" in patch_groups:
    n = len(patch_groups["l0_redline"])
    suggestions.append({
        "patch": "l0_redline (大额 / 冻结 短词)",
        "wrong_count": n,
        "root_cause": "L0 词典 '大额'/'冻结' 短词太宽 — '大额存单' (产品咨询, 不是大额转账) / '卡冻结了?' (用户描述状态, 不是冻结请求)",
        "fix_direction": "收紧: L0 词典删 '大额' 单独 (v3.10.1 已做), 进一步删 '冻结' 单独 (用户描述状态 ≠ 冻结请求), 只保留 '冻结卡'/'紧急冻结'/'马上冻结'",
        "priority": "P0",
    })

# 2.4 security_aml_cross_border 误伤 — 单纯"美元汇率" 查汇率 (无汇款动作) 也被红线
if "security_aml_cross_border" in patch_groups:
    n = len(patch_groups["security_aml_cross_border"])
    suggestions.append({
        "patch": "security_aml_cross_border",
        "wrong_count": n,
        "root_cause": "P0 patch '境外/国外/美元' 把单纯查汇率 query 也误吞 (例: '美元汇率' / '美元汇率多少')",
        "fix_direction": "收紧: cross_border patch 必须有 '汇款/汇钱/转给+境外/汇 X 元' 动作信号才触发; 单独 '美元汇率/外汇行情' 不触发",
        "priority": "P1",
    })

# 2.5 cons_urg_lock 误伤 — "密码输错被锁了"
if "cons_urg_lock" in patch_groups:
    n = len(patch_groups["cons_urg_lock"])
    suggestions.append({
        "patch": "cons_urg_lock",
        "wrong_count": n,
        "root_cause": "P0 patch '被锁/锁了' 把 '密码输错被锁了' (P1 业务咨询) 也当 P0 转人工",
        "fix_direction": "收紧: 当 query 含 '密码/登录' + '被锁' 时降级到 password_forget_with_disambiguation (P1)",
        "priority": "P1",
    })

for s in suggestions:
    print(f"\n### {s['patch']} — 误伤 {s['wrong_count']} 条")
    print(f"   根因: {s['root_cause']}")
    print(f"   修复: {s['fix_direction']}")
    print(f"   优先级: {s['priority']}")

# 3. Save updated A2
a2["patch_groups"] = {k: v for k, v in patch_groups.items()}
a2["patch_summary"] = patch_summary
a2["suggestions"] = suggestions
a2["total_suggested_p1_recovery"] = sum(s["wrong_count"] for s in suggestions if s["priority"] == "P0")
A2_PATH.write_text(json.dumps(a2, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n✓ A2 详细分析已写入: {A2_PATH}")

c.close()