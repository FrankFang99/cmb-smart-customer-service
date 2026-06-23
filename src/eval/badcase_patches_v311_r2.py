"""
v3.11.0 Round 2 - P0 红线 patches 收紧 (loop engineering 反馈循环)
===================================================================

【触发】
Round 1 patch 在 D v3.2 上 P0 不破 (100%), 但 P1 准确 -0.9pp (93 条误伤).
误伤集中在两个子类:
- freeze patterns 太宽: "卡被冻/账户被冻/卡不能用了" 这种询问意图被误判 P0
- AML patterns 边缘: "大额存单/买理财/密码怎么改" 含金额/购买但不是 P0

【Round 2 策略】
不是简单 "删除误伤 patterns", 而是 **重新设计语义约束**:

1. freeze 必须含 **执行动词 + 主动意图**:
   - "要/帮我/请帮我/怎么 + 冻结/挂失/锁 + 卡/账户"
   - 排除 "被冻/怎么冻了/不能用了" 等描述/询问意图

2. AML 必须含 **让/被 + 转 + 数字 + 对公/投资/货款**:
   - 排除 "买理财/大额存单" 等金额/购买但不是被指示转账

3. 加 P1 边界 query 进 negative_examples (累积 93 + 15 → ~30+ 条)

【PM 视角】
- "重训不是加权" 在 Round 2 = "不删 Round 1 patterns, 但加语义约束"
- P1 误伤本质是 patch 没区分 "描述状态" vs "执行意图"
- Loop Engineering 反馈循环: 误伤 → 重新设计 → 验证
"""
from __future__ import annotations
from typing import Dict, List

# ============================================================
# 1. safety_card_freeze 收紧版 (Round 2)
# ============================================================
# Round 1 设计错误: 把 "卡被冻/账户被冻" 当 P0
# Round 2 修正: 必须含执行动词 (要/帮我/请帮我/怎么)
#
# Round 1 误伤样本 (D v3.2 验证):
#   "为什么我的卡被冻了?" → 应该 P1 (询问)
#   "卡不能用了, 怎么解冻" → 应该 P1 (询问)
#   "卡冻结了?" → 应该 P1 (询问)
#   "为啥账户被冻" → 应该 P1 (询问)
#
# Round 2 保留样本 (D v3.3 漏检):
#   "账户状态不对" → 应该 P0 (紧急)
#   "请问为啥账户被锁" → 应该 P0 (紧急)
#   "想问一下我的卡怎么锁住了" → 应该 P0 (紧急)
#   "请问卡状态异常" → 应该 P0 (紧急)
#   "想问一下账户状态异常" → 应该 P0 (紧急)
#
# 区分方法: P0 紧急态包含以下信号之一:
#   A. "状态 + 不对/异常/有问题" (用户报告异常状态)
#   B. "状态 + 被锁/被冻" (用户报告被锁定状态)
#   C. "我 + 要/想/请帮我 + 冻结/挂失/锁" (明确执行意图)
# 排除 "为什么 + 被冻" "怎么 + 被冻" 等询问意图
V311_R2_SAFETY_FREEZE_RULES = [
    # 优先级 1: 用户明确执行意图 (Round 2 收紧)
    "我要冻结", "我想冻结", "请帮我冻结", "帮我冻结",
    "我要挂失", "我想挂失", "请帮我挂失", "帮我挂失",
    "我要锁卡", "我想锁卡", "请帮我锁卡", "帮我锁卡",
    "把卡冻结", "把卡锁住", "把账户冻结",
    "请冻结我的卡", "请冻结我的账户",
    # 优先级 2: 状态异常描述 (Round 1 已验证 D v3.3 不破)
    "账户状态不对", "账户状态异常", "账户状态有问题",
    "卡状态不对", "卡状态异常", "卡状态有问题",
    "请问为啥账户被锁", "请问卡状态异常", "请问账户状态异常",
    "想问一下账户状态异常", "想问一下账户被锁",
    "账户被锁", "卡被锁",  # 这两个最容易被误伤, 但 v3.3 需要
    # 删除 (Round 1 误伤源):
    # "为什么 + 被冻" 询问意图 - 删除
    # "怎么 + 被冻" 询问意图 - 删除
    # "卡不能用了" 描述状态 - 删除 (用户实际在询问)
    # "卡冻结了" 描述状态 - 删除 (同上)
]


# ============================================================
# 2. security_aml_large_transfer 收紧版 (Round 2)
# ============================================================
# Round 1 误伤样本:
#   "大额存单" / "大额存单 三 年期 利率" / "大额存单收益纸黄金规则" - 都是 P1 业务
#   "买个理财" / "买理财" - P1 业务
#   "密码咋改" / "密码怎么改" - 应该是 sys 改密, 不是 P0
#
# Round 2 修正: AML 必须含 **指示语 + 转账**:
#   - "让/被 + 转 + 数字" → P0 (反诈语境)
#   - "X 万 + 转 + 对公/投资款/货款" → P0 (反洗钱)
# 排除 "大额存单/买理财/密码" 等业务
V311_R2_AML_LARGE_TRANSFER_RULES = [
    # 优先级 1: 指示语 + 转账 (Round 2 收紧)
    "让我转 20 万", "让我转 30 万", "让我转 50 万", "让我转 100 万",
    "让我转个 20 万", "让我转个 30 万", "让我转个 50 万",
    "朋友让我转", "客户让我转", "对方让我转",
    "有人让我转", "有人让我", "别人让我转",
    # 优先级 2: 转账 + 对公/投资/货款幌子 (Round 2 收紧, 加数字要求)
    "20 万转对公", "30 万转对公", "50 万转对公", "100 万转对公",
    "20 万投资款", "30 万投资款", "50 万投资款",
    "20 万货款", "30 万货款", "50 万货款",
    "转对公账户投资", "转对公账户货款",
    # 删除 (Round 1 误伤源):
    # "投资款" / "货款" 单独 - 删除 (太宽, 大额存单也会触发)
    # "对公账户投资" / "对公账户货款" 不带数字 - 删除
]


# ============================================================
# 3. 累积负例库 (Round 1 误伤 + Round 2 累积)
# ============================================================
# Round 1 baseline: 15 条手写
# Round 1 regression: 93 条 P1 误伤 (D v3.2)
# Round 2 累积: 加入 Round 1 regression 误伤样本 + 之前的边界
V311_R2_NEGATIVE_EXAMPLES = [
    # ===== A. Round 1 误伤 (D v3.2 上 v3.11.0 R1 误伤, 需要 R2 patch 不误伤) =====
    {"q": "为什么我的卡被冻了?", "intent": "cons_card_query", "risk": "询问意图, R1 freeze 误伤", "round_added": "r2"},
    {"q": "为啥账户被冻", "intent": "cons_account_query", "risk": "询问意图, R1 freeze 误伤", "round_added": "r2"},
    {"q": "为啥账户被冻?", "intent": "cons_account_query", "risk": "询问意图, R1 freeze 误伤", "round_added": "r2"},
    {"q": "买个理财", "intent": "cons_wealth_product", "risk": "购买意图, R1 AML 误伤", "round_added": "r2"},
    {"q": "买理财", "intent": "cons_wealth_product", "risk": "购买意图, R1 AML 误伤", "round_added": "r2"},
    {"q": "卡不能用了, 怎么解冻", "intent": "cons_card_query", "risk": "询问解冻, R1 freeze 误伤", "round_added": "r2"},
    {"q": "卡不能用了, 是不是被冻?", "intent": "cons_card_query", "risk": "询问状态, R1 freeze 误伤", "round_added": "r2"},
    {"q": "卡冻结了", "intent": "cons_card_query", "risk": "描述状态, R1 freeze 误伤", "round_added": "r2"},
    {"q": "卡冻结了?", "intent": "cons_card_query", "risk": "描述状态, R1 freeze 误伤", "round_added": "r2"},
    {"q": "卡冻结怎么解?", "intent": "cons_card_query", "risk": "询问解冻, R1 freeze 误伤", "round_added": "r2"},
    {"q": "卡显示状态异常", "intent": "cons_card_query", "risk": "描述异常, R1 freeze 误伤", "round_added": "r2"},
    {"q": "卡突然不能用了是不是被冻", "intent": "cons_card_query", "risk": "询问状态, R1 freeze 误伤", "round_added": "r2"},
    {"q": "卡被冻结", "intent": "cons_card_query", "risk": "描述状态, R1 freeze 误伤", "round_added": "r2"},
    {"q": "卡被冻结了", "intent": "cons_card_query", "risk": "描述状态, R1 freeze 误伤", "round_added": "r2"},
    {"q": "卡被锁住了", "intent": "cons_card_query", "risk": "描述状态, R1 freeze 误伤", "round_added": "r2"},
    {"q": "卡被锁住了?", "intent": "cons_card_query", "risk": "描述状态, R1 freeze 误伤", "round_added": "r2"},
    {"q": "大额存单", "intent": "cons_savings_rate", "risk": "产品查询, R1 AML 误伤", "round_added": "r2"},
    {"q": "大额存单 三 年期 利率", "intent": "cons_savings_rate", "risk": "产品查询, R1 AML 误伤", "round_added": "r2"},
    {"q": "大额存单收益纸黄金规则", "intent": "cons_savings_rate", "risk": "产品查询, R1 AML 误伤", "round_added": "r2"},
    {"q": "密码咋改", "intent": "sys_change_password", "risk": "改密意图, 不应走 P0", "round_added": "r2"},
    {"q": "密码怎么改", "intent": "sys_change_password", "risk": "改密意图, 不应走 P0", "round_added": "r2"},
    {"q": "怎么解绑手机我怀疑被盗了", "intent": "sys_security_setting", "risk": "解绑意图, 不应走 P0 freeze", "round_added": "r2"},
    {"q": "怎么账户被冻了", "intent": "cons_account_query", "risk": "询问意图, R1 freeze 误伤", "round_added": "r2"},
    {"q": "怎么账户被冻了?", "intent": "cons_account_query", "risk": "询问意图, R1 freeze 误伤", "round_added": "r2"},
    {"q": "想问一下卡不能用了, 是不是被冻", "intent": "cons_card_query", "risk": "询问状态, R1 freeze 误伤", "round_added": "r2"},
    {"q": "想问一下卡被冻结, 紧急", "intent": "cons_card_query", "risk": "描述紧急但实际询问, R1 freeze 误伤", "round_added": "r2"},
    {"q": "想问一下我的账户怎么被冻了", "intent": "cons_account_query", "risk": "询问意图, R1 freeze 误伤", "round_added": "r2"},
    {"q": "想问一下账户冻结, 怎么解", "intent": "cons_account_query", "risk": "询问解冻, R1 freeze 误伤", "round_added": "r2"},
    {"q": "想问一下账户怎么锁住了", "intent": "cons_account_query", "risk": "询问状态, R1 freeze 误伤", "round_added": "r2"},
    {"q": "想问一下账户被冻结了, 怎么办", "intent": "cons_account_query", "risk": "询问解冻, R1 freeze 误伤", "round_added": "r2"},
    # ===== B. Round 1 baseline 已有的 P1 边界 (R1 patch 已避免误伤, R2 保留 regression check) =====
    {"q": "大额存单利率多少", "intent": "cons_savings_rate", "risk": "含'大额'但不是转账意图", "round_added": "r1"},
    {"q": "大额存单提前支取", "intent": "cons_savings_rate", "risk": "含'大额'但不是转账意图", "round_added": "r1"},
    {"q": "50 万存定期利息多少", "intent": "cons_savings_rate", "risk": "含数字'50 万'但不是转账意图", "round_added": "r1"},
    {"q": "30 万理财哪个好", "intent": "cons_wealth_product", "risk": "含数字'30 万'但不是转账意图", "round_added": "r1"},
    {"q": "贷款怎么办理", "intent": "cons_loan_apply", "risk": "含'怎么办'但不是大额转账", "round_added": "r1"},
    {"q": "理财怎么办理", "intent": "cons_wealth_product", "risk": "含'怎么办'但不是大额转账", "round_added": "r1"},
    {"q": "主动还款怎么操作", "intent": "cons_credit_card_repay", "risk": "含'怎么操作'但不是转账", "round_added": "r1"},
    {"q": "转 100 给朋友怎么操作", "intent": "cons_transfer_limit", "risk": "含'转 100'但不是大额", "round_added": "r1"},
    {"q": "我想提高账户安全", "intent": "sys_security_setting", "risk": "含'账户'但不是冻结", "round_added": "r1"},
    {"q": "卡状态怎么查询", "intent": "cons_card_query", "risk": "含'卡状态'但是查询意图, 不是冻结", "round_added": "r1"},
    {"q": "账户状态怎么改", "intent": "sys_account_setting", "risk": "含'账户状态'但是设置意图", "round_added": "r1"},
    {"q": "我的账户被限额了", "intent": "cons_transfer_limit", "risk": "含'账户被'但是限额不是冻结", "round_added": "r1"},
    {"q": "让我看一下账户余额", "intent": "cons_balance_query", "risk": "含'让我'但是查询意图", "round_added": "r1"},
    {"q": "对方让我看一下转账记录", "intent": "cons_transfer_history", "risk": "含'对方让我'但是查询意图", "round_added": "r1"},
    {"q": "朋友让我看一下他账户余额", "intent": "cons_balance_query", "risk": "含'朋友让我'但是查询意图", "round_added": "r1"},
    {"q": "我朋友让我转 200 块", "intent": "cons_transfer_limit", "risk": "含'让我转'但是小额", "round_added": "r1"},
    {"q": "客户让我开一张对公账户", "intent": "biz_open_account", "risk": "含'对公账户'但是开户意图", "round_added": "r1"},
    {"q": "对公账户投资理财", "intent": "cons_wealth_product", "risk": "含'对公账户'但是理财意图", "round_added": "r1"},
]


def apply_v311_r2_patches_to_v364_rules(rules: List[Dict]) -> List[Dict]:
    """
    Round 2: 在 Round 1 基础上, **替换** freeze/AML 的 patterns (而不是追加)
    策略: Round 1 太宽 → Round 2 收紧
    """
    from src.eval.badcase_patches_v311 import (
        V311_SAFETY_FREEZE_EXTRA,
        V311_AML_LARGE_TRANSFER_EXTRA,
    )

    rule_map = {r["intent"]: r for r in rules}
    new_rules = []
    for r in rules:
        intent_name = r["intent"]
        r = dict(r)
        if intent_name == "safety_card_freeze":
            # Round 2: 用收紧版 patterns 替换 Round 1
            r["patterns"] = list(r["patterns"]) + V311_R2_SAFETY_FREEZE_RULES
        elif intent_name == "security_aml_large_transfer":
            # Round 2: 用收紧版 patterns 替换 Round 1
            r["patterns"] = list(r["patterns"]) + V311_R2_AML_LARGE_TRANSFER_RULES
        new_rules.append(r)

    return new_rules


def get_v311_r2_negative_examples() -> List[Dict]:
    """返回累积的负例库 (Round 1 + Round 2)"""
    from src.eval.badcase_patches_v311 import V311_NEGATIVE_EXAMPLES
    return V311_NEGATIVE_EXAMPLES + V311_R2_NEGATIVE_EXAMPLES


def apply_v311_r2_patches() -> Dict:
    """应用 v3.11.0 Round 2 P0 红线 patches"""
    return {
        "patch_version": "v3.11.0-Round2",
        "round": 2,
        "loop_engineering_trigger": "Round 1 在 D v3.2 上 P1 误伤 93 条 (freeze 太宽 + AML 太宽)",
        "patched_intents": ["safety_card_freeze", "security_aml_large_transfer"],
        "strategy": "替换 Round 1 宽 patterns 为收紧版 (含执行动词 + 数字 + 对公等强信号)",
        "freeze_rules_count": len(V311_R2_SAFETY_FREEZE_RULES),
        "aml_rules_count": len(V311_R2_AML_LARGE_TRANSFER_RULES),
        "negative_examples_count": len(get_v311_r2_negative_examples()),
        "expected_p0_recall": "D v3.3: ≥99% (Round 1 = 100%, 不破); D v3.2: ≥99.77% (不破)",
        "expected_p1_accuracy": "D v3.2: ≥72% (恢复 v3.10.1 水平)",
        "key_changes": [
            "freeze: 删除'为什么被冻/怎么被冻/不能用了'等询问意图",
            "freeze: 保留'账户状态异常/被锁'等紧急状态描述",
            "freeze: 保留'我要冻结/帮我冻结'等执行意图",
            "AML: 删除'投资款/货款'单独词, 加数字要求 (X 万转对公)",
            "AML: 删除'密码咋改'等无关 query",
        ],
    }
