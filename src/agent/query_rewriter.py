"""
v3.5.0 Query 改写增强
=======================

业界对齐: 招行小招 / 蚂蚁 2024-2026 升级
- 代词补全 (Pronoun Resolution)
- 意图明确化 (Query Disambiguation)
- HyDE 升级 (用 LLM 假设答案反向查, 0 依赖下用模板假设)

设计:
- 3 种改写策略独立可观测
- 0 依赖 (HyDE 用模板假设, v4.0 接真 LLM)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

try:
    from src.agent.conversation_manager import ConversationManager
except ImportError:
    ConversationManager = None


# ============================================================
# 代词补全
# ============================================================
PRONOUN_MAPPING = {
    "我那个": "[前文对象]",
    "那个": "[前文对象]",
    "它": "[前文对象]",
    "这个": "[前文对象]",
    "那": "[前文对象]",
    "这": "[前文对象]",
    "这卡": "[前文卡片]",
    "那卡": "[前文卡片]",
    "我": "[当前用户]",
    "我的": "[当前用户]的",
    "这个额度": "[前文对象]额度",
    "那个额度": "[前文对象]额度",
    "多少钱": "[前文对象]金额",
    "怎么弄": "[前文对象]操作",
    "怎么办": "[前文对象]处理",
}


class PronounResolver:
    """代词补全器"""

    def __init__(self):
        self.pronouns = list(PRONOUN_MAPPING.keys())

    def resolve(
        self, user_input: str, history: Optional[List[Dict]] = None
    ) -> Tuple[str, bool]:
        """
        代词补全
        Returns: (改写后 query, 是否做了改写)
        """
        if not history:
            return user_input, False
        # 找最近一轮的对象
        last_subject = None
        for turn in reversed(history):
            if turn.get("role") == "user":
                content = turn.get("content", "")
                if content and not any(p in content for p in self.pronouns):
                    last_subject = content[:30]
                    break
        if not last_subject:
            return user_input, False
        # 替换代词
        rewritten = user_input
        replaced = False
        for pronoun, template in PRONOUN_MAPPING.items():
            if pronoun in rewritten:
                if "[前文对象]" in template:
                    rewritten = rewritten.replace(pronoun, last_subject)
                    replaced = True
                elif "[当前用户]" in template:
                    rewritten = rewritten.replace(pronoun, template)
                    replaced = True
        return rewritten, replaced


# ============================================================
# 意图明确化 (Query Disambiguation)
# ============================================================
AMBIGUOUS_PATTERNS = {
    "怎么弄": ["怎么激活信用卡", "怎么挂失", "怎么改密码", "怎么还款", "怎么开卡"],
    "怎么办": ["怎么激活", "怎么挂失", "怎么改密码", "怎么还款"],
    "怎么操作": ["怎么激活", "怎么挂失", "怎么改密码"],
    "怎么用": ["怎么用 App", "怎么用信用卡", "怎么用手机银行"],
    "怎么查": ["怎么查余额", "怎么查账单", "怎么查积分", "怎么查额度"],
    "怎么样": ["信用卡怎么样", "理财产品怎么样", "贷款怎么样"],
    "推荐": ["推荐信用卡", "推荐理财产品", "推荐贷款"],
    "那个": ["信用卡", "账户", "理财产品"],
    "这个": ["信用卡", "账户", "理财产品"],
}


class QueryDisambiguator:
    """意图明确化 (把口语 query 转成标准 query)"""

    def __init__(self):
        self.patterns = AMBIGUOUS_PATTERNS

    def disambiguate(self, user_input: str) -> Tuple[List[str], bool]:
        """
        明确化 query
        Returns: (候选 queries 列表, 是否做了改写)
        """
        candidates = []
        for pattern, expansions in self.patterns.items():
            if pattern in user_input:
                candidates.extend(expansions)
                return list(set(candidates)), True
        return [user_input], False


# ============================================================
# HyDE (Hypothetical Document Embeddings)
# ============================================================
HYDE_TEMPLATES = {
    "info_acc_balance": "查询账户余额的方法: 登录招商银行 App → 我的 → 账户余额, 或拨打 95555, 或网银查询。",
    "info_bill_amount": "信用卡账单金额查询: 登录 App → 信用卡 → 账单查询, 或发送短信 ZD#卡号后四位 到 95555。",
    "info_branch": "招商银行网点查询: 拨打 95555 或登录官网 → 网点查询, 或使用 App 内的网点查询功能。",
    "info_phone": "招商银行客服电话: 95555 (个人业务) / 400-880-5535 (信用卡业务)。",
    "biz_card_activate": "信用卡激活方法: 登录招商银行 App → 卡片管理 → 卡片激活, 或拨打卡背面客服电话激活。",
    "biz_card_loss": "信用卡挂失步骤: 立即拨打 95555 转人工挂失, 或登录 App → 卡片管理 → 一键挂失。",
    "biz_tran_limit": "转账限额规则: 手机银行默认单笔 5 万 / 单日 20 万, U盾客户更高。",
    "sec_fraud_report": "反诈骗处理: 立即挂失所有招行卡片, 拨打 110 报警, 保留诈骗证据。",
    "sales_wealth_prod": "理财产品推荐: 朝朝宝 (活期理财) / 日日盈 (短期理财), 预期年化 1.8%-3.2%。",
    "sales_credit_prod": "信用卡推荐: Young 卡 (年轻人首卡) / 标准信用卡 (通用)。",
    "sys_greeting": "你好, 欢迎使用招商银行智能客服。",
}


class HydeExpander:
    """HyDE 假设文档扩展 (用模板生成假设答案, 反向增强检索)"""

    def __init__(self):
        self.templates = HYDE_TEMPLATES

    def expand(self, user_input: str, intent: str = "") -> str:
        """
        生成假设答案
        """
        if intent and intent in self.templates:
            return self.templates[intent]
        # 关键词匹配
        u = user_input.lower()
        if "余额" in user_input:
            return self.templates["info_acc_balance"]
        if "账单" in user_input or "多少钱" in user_input:
            return self.templates["info_bill_amount"]
        if "网点" in user_input or "分行" in user_input:
            return self.templates["info_branch"]
        if "电话" in user_input or "热线" in user_input:
            return self.templates["info_phone"]
        if "激活" in user_input:
            return self.templates["biz_card_activate"]
        if "挂失" in user_input or "丢了" in user_input:
            return self.templates["biz_card_loss"]
        if "限额" in user_input:
            return self.templates["biz_tran_limit"]
        if "理财" in user_input or "朝朝宝" in user_input:
            return self.templates["sales_wealth_prod"]
        if "信用卡" in user_input and "推荐" in user_input:
            return self.templates["sales_credit_prod"]
        if "你好" in user_input or "您好" in user_input:
            return self.templates["sys_greeting"]
        return user_input  # 兜底


# ============================================================
# Query 改写器 (统一入口)
# ============================================================
class QueryRewriter:
    """Query 改写器 (代词补全 + 意图明确化 + HyDE)"""

    def __init__(
        self,
        pronoun: Optional[PronounResolver] = None,
        disambig: Optional[QueryDisambiguator] = None,
        hyde: Optional[HydeExpander] = None,
    ):
        self.pronoun = pronoun or PronounResolver()
        self.disambig = disambig or QueryDisambiguator()
        self.hyde = hyde or HydeExpander()

    def rewrite(
        self,
        user_input: str,
        history: Optional[List[Dict]] = None,
        intent: str = "",
    ) -> Dict[str, Any]:
        """
        改写 query
        Returns: {
            "original": 原 query,
            "rewritten": 改写后 query (主),
            "candidates": 候选 queries (用于多路检索),
            "hyde_doc": HyDE 假设文档,
            "operations": ["pronoun", "disambig", "hyde"],
        }
        """
        operations = []
        # 1. 代词补全
        rewritten, p_done = self.pronoun.resolve(user_input, history)
        if p_done:
            operations.append("pronoun")
        # 2. 意图明确化
        candidates, d_done = self.disambig.disambiguate(rewritten)
        if d_done:
            operations.append("disambig")
        else:
            candidates = [rewritten]
        # 3. HyDE
        hyde_doc = self.hyde.expand(rewritten, intent)
        if hyde_doc != rewritten:
            operations.append("hyde")
        return {
            "original": user_input,
            "rewritten": rewritten,
            "candidates": candidates,
            "hyde_doc": hyde_doc,
            "operations": operations,
        }


# ============================================================
# 工厂
# ============================================================
def get_query_rewriter() -> QueryRewriter:
    """获取 Query 改写器"""
    return QueryRewriter()
