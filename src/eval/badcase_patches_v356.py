"""
v3.5.6 Badcase 修复补丁 v3 (修 sales/cons/sec 类)
===============================================

修复目标:
- sales 22.6% -> 70%+
- cons 49.5% -> 70%+
- sec 51.8% -> 70%+
- sys_greeting/thanks 误判: 修复 LLM 兜底前的"业务词优先"判断

根因 (v3.5.6-1 分析):
1. "你好, xxx" 模板让 LLM cascade L3 兜底把业务 query 判为 sys_greeting
2. "xxx 谢谢" 模板让 LLM cascade L3 兜底把业务 query 判为 sys_thanks
3. v3.5.6-1 已修改模板去掉问候词

新增 12 条意图规则 + 模板前缀修正 + LLM 兜底前预处理:
"""

from __future__ import annotations

from typing import Any, Dict, List

# ============================================================
# 1. 扩展意图规则 (从 8 条 -> 20 条)
# ============================================================
V356_INTENT_RULES = [
    # ----- sales 类增强 (15 -> 30+) -----
    # 信用卡
    {"patterns": ["申请信用卡", "想办信用卡", "想申请信用卡", "办信用卡", "我想办张卡"],
     "intent": "cons_prod_credit",
     "reason": "客户表达的是'咨询'申请"},
    {"patterns": ["办什么信用卡好", "办什么卡", "推荐什么卡", "办哪种卡", "哪张卡好"],
     "intent": "sales_credit_prod",
     "reason": "客户在问'办什么卡', 是营销"},
    # 理财
    {"patterns": ["有什么好理财", "哪个理财好", "理财推荐哪个", "理财哪个好", "什么理财值得买"],
     "intent": "cons_prod_wealth",
     "reason": "客户问'有什么好', 是咨询"},
    {"patterns": ["推荐个理财", "推荐理财", "理财推荐", "想了解理财", "买什么理财"],
     "intent": "sales_wealth_prod",
     "reason": "客户要'推荐', 是营销"},
    # 贷款
    {"patterns": ["招行信用贷", "贷款产品", "招行贷款", "信用贷款", "贷款推荐", "借点钱"],
     "intent": "sales_loan_prod",
     "reason": "询问贷款产品"},
    {"patterns": ["贷款怎么办", "怎么贷款", "贷款申请", "想贷款", "如何贷款"],
     "intent": "cons_prod_loan",
     "reason": "询问贷款咨询"},
    # ----- cons 类增强 -----
    {"patterns": ["转账到别的银行", "转到别的银行", "跨行转账", "转他行", "转别的银行"],
     "intent": "biz_tran_external",
     "reason": "'别的银行'/'跨行'/'他行' 强匹配"},
    {"patterns": ["转钱到招行", "转到招行卡", "转给招行", "转招行"],
     "intent": "biz_tran_internal",
     "reason": "明确提到'转钱'和'招行卡'"},
    {"patterns": ["查一下交易明细", "查交易明细", "看交易明细", "查明细", "想查交易明细"],
     "intent": "info_acc_detail",
     "reason": "客户要'查'的是'交易明细'"},
    # ----- biz 类增强 -----
    {"patterns": ["信用卡怎么激活", "信用卡激活", "怎么激活卡", "怎么开卡", "怎么激活信用卡"],
     "intent": "biz_card_activate",
     "reason": "明确询问'激活'"},
    # ----- info 类增强 -----
    {"patterns": ["有什么", "有哪些", "有什么推荐的", "推荐什么"],
     "intent": "sales_credit_prod",  # 默认营销意图
     "reason": "客户要'推荐', 默认匹配 sales"},
    # ----- 保险类模糊 -> 销售 -----
    {"patterns": ["理财产品", "稳健理财", "高收益理财", "理财哪款好", "朝朝宝怎么样", "朝朝宝收益", "日日盈"],
     "intent": "sales_wealth_prod",
     "reason": "理财产品推荐类查询, 走 sales"},
    # ----- 投诉/转人工优先 -----
    {"patterns": ["我要投诉", "客服态度差", "服务质量差", "投诉处理", "服务投诉", "对服务不满意", "要投诉"],
     "intent": "cons_comp_service",
     "reason": "投诉类走 cons 咨询"},
    # ----- 反诈类 (防骗子) -----
    {"patterns": ["骗子", "诈骗", "骗了", "疑似诈骗", "碰到诈骗", "可能是诈骗", "怀疑诈骗", "好像诈骗", "是否诈骗"],
     "intent": "sec_fraud_report",
     "reason": "诈骗词应触发反诈 P0"},
    # ----- 盗刷类 -----
    {"patterns": ["盗刷", "被盗刷", "被刷", "卡里少了钱, 不是我的", "陌生扣款", "不是我的扣款", "卡被刷了"],
     "intent": "sec_stolen_card",
     "reason": "盗刷相关应触发 sec P0"},
]


# ============================================================
# 2. LLM 兜底前预处理 (v3.5.6 修复: 业务词优先)
# ============================================================
def preprocess_user_input(user_input: str) -> str:
    """
    LLM 兜底前预处理, 去除"你好"/"谢谢"等寒暄词前缀/后缀
    (避免 LLM cascade 把业务 query 误判为 sys_greeting/thanks)

    v3.5.6 修复: 即使种子问题里加了"你好", 在 LLM 兜底前先去掉
    """
    import re
    text = user_input.strip()
    # 去掉前缀问候
    for prefix in ["你好, ", "您好, ", "你好,", "您好,", "你好", "您好", "hi", "哈喽", "在吗, ", "在吗"]:
        if text.lower().startswith(prefix.lower()):
            text = text[len(prefix):].lstrip(" ,，。.?!?？")
            break
    # 去掉后缀感谢
    for suffix in ["谢谢", "多谢", "thx", "感谢", "非常感谢", "3Q"]:
        if text.lower().endswith(suffix.lower()):
            text = text[:-len(suffix)].rstrip(" ,，。.?!?？")
            break
    return text


# ============================================================
# 3. v3.5.6 修复后预期
# ============================================================
V356_EXPECTED = {
    "intent_accuracy": {
        "before_overall": 60.89,  # v3.5.5 holdout
        "target_overall": 75.0,
        "before_sales": 22.6,
        "target_sales": 70.0,
        "before_cons": 49.5,
        "target_cons": 70.0,
        "before_sec": 51.8,
        "target_sec": 70.0,
        "before_sys": 60.3,
        "target_sys": 85.0,  # 修问候词后应更高
    },
    "p0_recall": {
        "before": 76.01,  # v3.5.5 holdout
        "target": 80.0,
    },
}


# ============================================================
# 4. 工厂
# ============================================================
def apply_v356_patches():
    return {
        "intent_rules_count": len(V356_INTENT_RULES),
        "expected": V356_EXPECTED,
        "patch_version": "v3.5.6",
    }


def get_intent_rules_v356() -> List[Dict[str, Any]]:
    return V356_INTENT_RULES
