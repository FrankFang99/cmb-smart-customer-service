"""
v3.5.5 Badcase 修复补丁 v2 (L0 词典扩 30 词)
==========================================

对比 v3.5.1:
- v3.5.1: 14 词 (硬触发, 漏口语化 P0)
- v3.5.5: 30+ 词 (含口语化变体, 覆盖国有大行业务场景)

新增加 (16 词):
- 卡被锁 / 卡被锁住 / 卡不能用 (口语化 sec_freeze)
- 盗刷 / 被盗刷 / 陌生扣款 (sec_stolen_card 口语化)
- 卡里少了钱 / 不是我的消费 (cons_urg_loss 口语化)
- 骗子 / 诈骗 / 骗了 (cons_comp 投诉类)
- 紧急 / 钱没了 / 钱被转走 (cons_urg_human 强化)
- 卡被封 / 账户被封 (sec_freeze 口语化)
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

# ============================================================
# 1. L0 词典扩 30 词 (覆盖口语化 P0)
# ============================================================
V355_L0_KEYWORDS: Dict[str, Dict[str, str]] = {
    # 紧急转人工 (核心)
    "转人工": {"category": "urg_human", "triggered_by": "cons_urg_human"},
    "需要人工服务": {"category": "urg_human", "triggered_by": "cons_urg_human"},
    "找人工": {"category": "urg_human", "triggered_by": "cons_urg_human"},
    "人工客服": {"category": "urg_human", "triggered_by": "cons_urg_human"},
    "转接人工": {"category": "urg_human", "triggered_by": "cons_urg_human"},
    "找真人": {"category": "urg_human", "triggered_by": "cons_urg_human"},
    "人工坐席": {"category": "urg_human", "triggered_by": "cons_urg_human"},
    # 账户异常冻结 (重点扩 - v3.5.3 30% 召回修复)
    "账户异常冻结": {"category": "sec_freeze", "triggered_by": "sec_freeze_unexpected"},
    "账户异常": {"category": "sec_freeze", "triggered_by": "sec_freeze_unexpected"},
    "账户被冻": {"category": "sec_freeze", "triggered_by": "sec_freeze_unexpected"},
    "卡被冻": {"category": "sec_freeze", "triggered_by": "sec_freeze_unexpected"},
    "卡冻结了": {"category": "sec_freeze", "triggered_by": "sec_freeze_unexpected"},
    "卡被锁": {"category": "sec_freeze", "triggered_by": "sec_freeze_unexpected"},  # 新
    "卡被锁住": {"category": "sec_freeze", "triggered_by": "sec_freeze_unexpected"},  # 新
    "账户被锁": {"category": "sec_freeze", "triggered_by": "sec_freeze_unexpected"},  # 新
    "卡不能用": {"category": "sec_freeze", "triggered_by": "sec_freeze_unexpected"},  # 新
    "卡突然不能用": {"category": "sec_freeze", "triggered_by": "sec_freeze_unexpected"},  # 新
    "卡被封": {"category": "sec_freeze", "triggered_by": "sec_freeze_unexpected"},  # 新
    # 盗刷 (口语化)
    "收到陌生消费": {"category": "sec_stolen", "triggered_by": "sec_stolen_card"},
    "陌生消费": {"category": "sec_stolen", "triggered_by": "sec_stolen_card"},
    "不是我消费": {"category": "sec_stolen", "triggered_by": "sec_stolen_card"},
    "卡被刷了": {"category": "sec_stolen", "triggered_by": "sec_stolen_card"},
    "卡被刷": {"category": "sec_stolen", "triggered_by": "sec_stolen_card"},
    "被盗刷": {"category": "sec_stolen", "triggered_by": "sec_stolen_card"},  # 新
    "盗刷": {"category": "sec_stolen", "triggered_by": "sec_stolen_card"},  # 新
    "陌生扣款": {"category": "sec_stolen", "triggered_by": "sec_stolen_card"},  # 新
    "不是我的扣款": {"category": "sec_stolen", "triggered_by": "sec_stolen_card"},  # 新
    "卡里少了钱": {"category": "sec_stolen", "triggered_by": "sec_stolen_card"},  # 新
    "不是我的消费": {"category": "sec_stolen", "triggered_by": "sec_stolen_card"},  # 新
    # 紧急损失
    "钱没了": {"category": "cons_urg_loss", "triggered_by": "cons_urg_loss"},  # 新
    "钱被转走": {"category": "cons_urg_loss", "triggered_by": "cons_urg_loss"},  # 新
    "钱不见了": {"category": "cons_urg_loss", "triggered_by": "cons_urg_loss"},  # 新
    "被诈骗了": {"category": "sec_fraud", "triggered_by": "sec_fraud_report"},
    "我被诈骗了": {"category": "sec_fraud", "triggered_by": "sec_fraud_report"},
    "被电信诈骗": {"category": "sec_fraud", "triggered_by": "sec_fraud_report"},
    # 投诉 + 诈骗词
    "骗子": {"category": "sec_fraud", "triggered_by": "sec_fraud_report"},  # 新
    "诈骗": {"category": "sec_fraud", "triggered_by": "sec_fraud_report"},  # 新
    "骗了": {"category": "sec_fraud", "triggered_by": "sec_fraud_report"},  # 新
    # 紧急
    "紧急": {"category": "cons_urg_loss", "triggered_by": "cons_urg_loss"},  # 新
}


# ============================================================
# 2. 8 条意图规则 (沿用 v3.5.1, 已是清晰规则)
# ============================================================
V355_INTENT_RULES = [
    {"patterns": ["申请信用卡", "想办信用卡", "想申请信用卡", "办信用卡"],
     "intent": "cons_prod_credit",
     "reason": "客户表达的是'咨询'申请"},
    {"patterns": ["转钱到招行", "转到招行卡", "转给招行", "转招行"],
     "intent": "biz_tran_internal",
     "reason": "明确提到'转钱'和'招行卡'"},
    {"patterns": ["有什么好理财", "哪个理财好", "理财推荐哪个", "理财哪个好"],
     "intent": "cons_prod_wealth",
     "reason": "客户问'有什么好', 是咨询"},
    {"patterns": ["转账到别的银行", "转到别的银行", "跨行转账", "转他行", "转别的银行"],
     "intent": "biz_tran_external",
     "reason": "'别的银行'/'跨行'/'他行' 强匹配"},
    {"patterns": ["查一下交易明细", "查交易明细", "看交易明细", "查明细"],
     "intent": "info_acc_detail",
     "reason": "客户要'查'的是'交易明细'"},
    {"patterns": ["办什么卡好", "办什么卡", "推荐什么卡", "办哪种卡"],
     "intent": "sales_credit_prod",
     "reason": "客户在问'办什么卡'"},
    {"patterns": ["信用卡怎么激活", "信用卡激活", "怎么激活卡", "怎么开卡"],
     "intent": "biz_card_activate",
     "reason": "明确询问'激活'"},
    {"patterns": ["推荐个理财", "推荐理财", "理财推荐"],
     "intent": "sales_wealth_prod",
     "reason": "客户要'推荐', 是营销意图"},
]


# ============================================================
# 3. 修复后预期效果
# ============================================================
V355_EXPECTED_IMPROVEMENT = {
    "p0_recall": {
        "before": "71.55% (v3.5.4 holdout)",
        "target": ">= 90%",
        "key_focus": "sec_freeze_unexpected (30% -> 80%+)",
    },
    "intent_accuracy": {
        "before": "72.50% (v3.5.4 holdout, 种子问题质量拖累)",
        "target": ">= 85%",
        "key_focus": "清晰种子 (v3.5.5 不再口语化过头)",
    },
    "l0_compliance": {
        "before": "100%",
        "target": "100% (保持)",
    },
}


# ============================================================
# 4. 工厂: 一键应用所有修复
# ============================================================
def apply_v355_patches():
    return {
        "l0_keywords_count": len(V355_L0_KEYWORDS),
        "intent_rules_count": len(V355_INTENT_RULES),
        "expected_improvement": V355_EXPECTED_IMPROVEMENT,
        "patch_version": "v3.5.5",
    }


def get_l0_keywords_v355() -> Dict[str, Dict[str, str]]:
    return V355_L0_KEYWORDS


def get_intent_rules_v355() -> List[Dict[str, Any]]:
    return V355_INTENT_RULES
