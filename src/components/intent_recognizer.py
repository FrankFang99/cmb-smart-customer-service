"""
阶梯式意图识别器
规则 -> 轻量模型 -> LLM 三级回退
"""
from enum import Enum
from typing import Optional, Tuple
from dataclasses import dataclass


class IntentType(str, Enum):
    """银行客服意图类型"""
    GREETING = "greeting"                    # 问候
    FAQ = "faq"                             # 常见问题咨询
    ACCOUNT_QUERY = "account_query"         # 账户查询
    BILL_QUERY = "bill_query"               # 账单查询
    BRANCH_QUERY = "branch_query"           # 网点查询
    COMPLAINT = "complaint"                # 投诉
    TRANSFER_GUIDE = "transfer_guide"      # 转账指引
    PRODUCT_QUERY = "product_query"        # 产品咨询
    CARD_MANAGE = "card_manage"            # 卡片管理
    HUMAN_SERVICE = "human_service"        # 转人工
    UNKNOWN = "unknown"                    # 未知


@dataclass
class IntentResult:
    """意图识别结果"""
    intent: IntentType
    confidence: float
    reasoning: str
    source: str  # "rule" | "model" | "llm"


class RuleBasedRecognizer:
    """规则引擎 - 处理高频指令"""

    # 高频关键词 -> 意图映射
    RULE_MAPPINGS = {
        # 转人工
        "转人工": IntentType.HUMAN_SERVICE,
        "人工服务": IntentType.HUMAN_SERVICE,
        "真人": IntentType.HUMAN_SERVICE,
        "客服": IntentType.HUMAN_SERVICE,
        "帮我转": IntentType.HUMAN_SERVICE,

        # 账户查询
        "余额": IntentType.ACCOUNT_QUERY,
        "账户": IntentType.ACCOUNT_QUERY,
        "多少钱": IntentType.ACCOUNT_QUERY,

        # 账单
        "账单": IntentType.BILL_QUERY,
        "还款": IntentType.BILL_QUERY,
        "消费": IntentType.BILL_QUERY,

        # 网点
        "网点": IntentType.BRANCH_QUERY,
        "分行": IntentType.BRANCH_QUERY,
        "支行": IntentType.BRANCH_QUERY,
        "在哪里": IntentType.BRANCH_QUERY,
        "地址": IntentType.BRANCH_QUERY,

        # 投诉
        "投诉": IntentType.COMPLAINT,
        "不满": IntentType.COMPLAINT,
        "太差": IntentType.COMPLAINT,
        "反馈": IntentType.COMPLAINT,

        # 转账
        "转账": IntentType.TRANSFER_GUIDE,
        "汇款": IntentType.TRANSFER_GUIDE,

        # 产品
        "理财": IntentType.PRODUCT_QUERY,
        "存款": IntentType.PRODUCT_QUERY,
        "贷款": IntentType.PRODUCT_QUERY,

        # 卡片管理
        "挂失": IntentType.CARD_MANAGE,
        "补卡": IntentType.CARD_MANAGE,
        "密码": IntentType.CARD_MANAGE,
    }

    def recognize(self, query: str) -> Optional[IntentResult]:
        """识别意图，返回 None 表示未命中"""
        query_lower = query.lower()

        for keyword, intent in self.RULE_MAPPINGS.items():
            if keyword in query_lower:
                return IntentResult(
                    intent=intent,
                    confidence=0.95,
                    reasoning=f"规则命中: 关键词 '{keyword}'",
                    source="rule"
                )

        return None


class IntentRecognizer:
    """三级意图识别器"""

    def __init__(self, settings):
        self.settings = settings
        self.rule_engine = RuleBasedRecognizer()

    def recognize(self, query: str, context: Optional[dict] = None) -> IntentResult:
        """
        阶梯式意图识别

        流程: 规则 -> 轻量模型 -> LLM
        """
        # 第一层：规则引擎
        result = self.rule_engine.recognize(query)
        if result and result.confidence >= self.settings.rule_confidence_threshold:
            return result

        # 第二层：轻量模型（待接入 sentence-transformers）
        # result = self.lightweight_model.predict(query)
        # if result and result.confidence >= self.settings.model_confidence_threshold:
        #     return result

        # 第三层：LLM 兜底
        return self._llm_fallback(query, context)

    def _llm_fallback(self, query: str, context: Optional[dict] = None) -> IntentResult:
        """LLM 意图解析"""
        from langchain_openai import ChatOpenAI
        from langchain.prompts import ChatPromptTemplate

        llm = ChatOpenAI(
            model=self.settings.llm_model,
            api_key=self.settings.deepseek_api_key,
            base_url=self.settings.deepseek_base_url,
            temperature=0.1
        )

        prompt = ChatPromptTemplate.from_template("""你是一个银行客服系统的意图识别器。

用户输入: {query}
{context}

请识别用户的意图，从以下类别中选择最匹配的:
- greeting: 问候
- faq: 常见问题咨询
- account_query: 账户查询
- bill_query: 账单查询
- branch_query: 网点查询
- complaint: 投诉
- transfer_guide: 转账指引
- product_query: 产品咨询
- card_manage: 卡片管理
- human_service: 转人工

直接输出意图名称和置信度(0-1)，格式如下:
意图: xxx
置信度: 0.xx
分析: xxx""")

        response = llm.invoke(prompt.format(query=query, context=f"上下文: {context}" if context else ""))
        content = response.content

        # 解析 LLM 返回
        lines = content.split('\n')
        intent_str = ""
        confidence = 0.5

        for line in lines:
            if line.startswith("意图:"):
                intent_str = line.replace("意图:", "").strip()
            if line.startswith("置信度:"):
                try:
                    confidence = float(line.replace("置信度:", "").strip())
                except:
                    confidence = 0.6

        # 映射到 IntentType
        intent_map = {e.value: e for e in IntentType}
        intent = intent_map.get(intent_str.lower(), IntentType.UNKNOWN)

        return IntentResult(
            intent=intent,
            confidence=confidence,
            reasoning=f"LLM识别: {content[:100]}...",
            source="llm"
        )