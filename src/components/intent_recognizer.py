"""
阶梯式意图识别器 v1.1
规则 -> 轻量模型 -> LLM 三级回退
支持8大类意图分类体系
"""
from enum import Enum
from typing import Optional, Tuple, List
from dataclasses import dataclass


class IntentType(str, Enum):
    """银行客服意图类型 v1.1 - 8大类"""

    # === 一级意图 ===
    # 查询类
    QUERY_BALANCE = "query_balance"           # 余额查询
    QUERY_BILL = "query_bill"                 # 账单查询
    QUERY_BANK_INFO = "query_bank_info"      # 开户行查询
    QUERY_PROGRESS = "query_progress"        # 进度查询
    QUERY_OTHER = "query_other"               # 其他查询

    # 交易操作类
    TRANSFER = "transfer"                     # 转账汇款
    PASSWORD_MANAGE = "password_manage"       # 密码管理
    CARD_LOSS = "card_loss"                   # 卡片挂失
    CARD_ACTIVATE = "card_activate"          # 卡片激活
    TRANSACTION_OTHER = "transaction_other"   # 其他操作

    # 咨询类
    CONSULT_RATE = "consult_rate"             # 利率咨询
    CONSULT_FEE = "consult_fee"              # 手续费咨询
    CONSULT_RULE = "consult_rule"             # 规则咨询
    CONSULT_ACTIVITY = "consult_activity"    # 活动咨询
    CONSULT_PRODUCT = "consult_product"      # 产品咨询

    # 服务转接类 [P0立即转]
    HUMAN_SERVICE = "human_service"          # 明确要求转人工
    COMPLAINT = "complaint"                  # 投诉
    SUGGESTION = "suggestion"                # 建议反馈
    URGENT_HELP = "urgent_help"              # 紧急求助

    # 营销咨询类
    MARKETING_WEALTH = "marketing_wealth"     # 理财产品咨询
    MARKETING_CREDIT = "marketing_credit"    # 信用卡咨询
    MARKETING_LOAN = "marketing_loan"       # 贷款产品咨询
    MARKETING_PROMO = "marketing_promo"      # 优惠活动咨询

    # 风险类 [P0立即转]
    ANTI_FRAUD = "anti_fraud"               # 反诈举报
    THEFT_REPORT = "theft_report"           # 盗刷反馈
    FREEZE_REQUEST = "freeze_request"       # 冻结申请
    SECURITY_EVENT = "security_event"       # 安全事件

    # 复杂需求
    CUSTOM_PLAN = "custom_plan"             # 定制理财方案
    LOAN_COMPARE = "loan_compare"           # 贷款方案对比
    COMPLEX_BUSINESS = "complex_business"   # 复杂业务办理
    HUMAN_INTERVENTION = "human_intervention"  # 需要人工介入

    # 模糊/无效意图
    ACCIDENTAL_TOUCH = "accidental_touch"   # 误触
    SEMANTIC_INVALID = "semantic_invalid"   # 语义不通
    UNKNOWN = "unknown"                     # 未知

    # 系统意图
    GREETING = "greeting"                   # 问候
    THANKS = "thanks"                       # 感谢


class IntentCategory:
    """意图分类工具"""

    # 一级分类映射
    PRIMARY_CATEGORIES = {
        "query": ["query_balance", "query_bill", "query_bank_info", "query_progress", "query_other"],
        "transaction": ["transfer", "password_manage", "card_loss", "card_activate", "transaction_other"],
        "consult": ["consult_rate", "consult_fee", "consult_rule", "consult_activity", "consult_product"],
        "service_transfer": ["human_service", "complaint", "suggestion", "urgent_help"],
        "marketing": ["marketing_wealth", "marketing_credit", "marketing_loan", "marketing_promo"],
        "risk": ["anti_fraud", "theft_report", "freeze_request", "security_event"],
        "complex": ["custom_plan", "loan_compare", "complex_business", "human_intervention"],
        "invalid": ["accidental_touch", "semantic_invalid", "unknown"],
    }

    # 需要P0立即转人工的意图
    P0_HUMAN_TRANSFER = [
        "human_service",  # 明确要求转人工
        "complaint",      # 投诉
        "urgent_help",    # 紧急求助
        "anti_fraud",     # 反诈举报
        "theft_report",   # 盗刷反馈
        "security_event", # 安全事件
    ]

    # 需要风险提示的意图
    NEED_RISK_DISCLOSURE = [
        "marketing_wealth",  # 理财
        "marketing_loan",    # 贷款
        "consult_product",  # 产品咨询
    ]

    @classmethod
    def is_p0_transfer(cls, intent: IntentType) -> bool:
        """判断是否需要P0立即转人工"""
        return intent.value in cls.P0_HUMAN_TRANSFER

    @classmethod
    def needs_risk_disclosure(cls, intent: IntentType) -> bool:
        """判断是否需要风险提示"""
        return intent.value in cls.NEED_RISK_DISCLOSURE

    @classmethod
    def get_primary_category(cls, intent: IntentType) -> str:
        """获取一级分类"""
        for category, intents in cls.PRIMARY_CATEGORIES.items():
            if intent.value in intents:
                return category
        return "unknown"


@dataclass
class IntentResult:
    """意图识别结果"""
    intent: IntentType
    confidence: float
    reasoning: str
    source: str  # "rule" | "model" | "llm"
    primary_category: str = ""  # 一级分类
    need_p0_transfer: bool = False  # 是否需要P0立即转


class RuleBasedRecognizer:
    """规则引擎 - 处理高频指令"""

    # 高频关键词 -> 意图映射
    RULE_MAPPINGS = {
        # === 服务转接类 [P0] ===
        "转人工": IntentType.HUMAN_SERVICE,
        "人工服务": IntentType.HUMAN_SERVICE,
        "真人": IntentType.HUMAN_SERVICE,
        "客服": IntentType.HUMAN_SERVICE,
        "帮我转": IntentType.HUMAN_SERVICE,
        "要人工": IntentType.HUMAN_SERVICE,
        "转接人工": IntentType.HUMAN_SERVICE,

        "投诉": IntentType.COMPLAINT,
        "不满": IntentType.COMPLAINT,
        "太差": IntentType.COMPLAINT,
        "举报": IntentType.COMPLAINT,
        "反馈": IntentType.COMPLAINT,

        "紧急": IntentType.URGENT_HELP,
        "快点": IntentType.URGENT_HELP,
        "急": IntentType.URGENT_HELP,

        # === 风险类 [P0] ===
        "诈骗": IntentType.ANTI_FRAUD,
        "被骗": IntentType.ANTI_FRAUD,
        "钓鱼": IntentType.ANTI_FRAUD,
        "盗刷": IntentType.THEFT_REPORT,
        "扣错钱": IntentType.THEFT_REPORT,
        "冻结": IntentType.FREEZE_REQUEST,
        "账户异常": IntentType.SECURITY_EVENT,
        "被盗": IntentType.SECURITY_EVENT,

        # === 查询类 ===
        "余额": IntentType.QUERY_BALANCE,
        "多少钱": IntentType.QUERY_BALANCE,
        "还有多少": IntentType.QUERY_BALANCE,

        "账单": IntentType.QUERY_BILL,
        "还款": IntentType.QUERY_BILL,
        "消费明细": IntentType.QUERY_BILL,
        "消费记录": IntentType.QUERY_BILL,

        "开户行": IntentType.QUERY_BANK_INFO,
        "开户": IntentType.QUERY_BANK_INFO,

        "进度": IntentType.QUERY_PROGRESS,
        "什么时候": IntentType.QUERY_PROGRESS,
        "多久": IntentType.QUERY_PROGRESS,

        # === 交易操作类 ===
        "转账": IntentType.TRANSFER,
        "汇款": IntentType.TRANSFER,
        "打钱": IntentType.TRANSFER,

        "密码": IntentType.PASSWORD_MANAGE,
        "改密": IntentType.PASSWORD_MANAGE,
        "忘记密码": IntentType.PASSWORD_MANAGE,

        "挂失": IntentType.CARD_LOSS,
        "丢了": IntentType.CARD_LOSS,
        "卡丢了": IntentType.CARD_LOSS,

        "激活": IntentType.CARD_ACTIVATE,
        "开卡": IntentType.CARD_ACTIVATE,

        # === 咨询类 ===
        "利率": IntentType.CONSULT_RATE,
        "利息": IntentType.CONSULT_RATE,
        "年化": IntentType.CONSULT_RATE,

        "手续费": IntentType.CONSULT_FEE,
        "收多少": IntentType.CONSULT_FEE,
        "费用": IntentType.CONSULT_FEE,

        "规则": IntentType.CONSULT_RULE,
        "规定": IntentType.CONSULT_RULE,
        "怎么操作": IntentType.CONSULT_RULE,

        "活动": IntentType.CONSULT_ACTIVITY,
        "优惠": IntentType.CONSULT_ACTIVITY,
        "打折": IntentType.CONSULT_ACTIVITY,

        # === 营销咨询类 ===
        "理财": IntentType.MARKETING_WEALTH,
        "基金": IntentType.MARKETING_WEALTH,
        "黄金": IntentType.MARKETING_WEALTH,

        "信用卡": IntentType.MARKETING_CREDIT,
        "办卡": IntentType.MARKETING_CREDIT,
        "申请卡": IntentType.MARKETING_CREDIT,

        "贷款": IntentType.MARKETING_LOAN,
        "借款": IntentType.MARKETING_LOAN,
        "信用贷": IntentType.MARKETING_LOAN,

        # === 复杂需求类 ===
        "帮我规划": IntentType.CUSTOM_PLAN,
        "怎么配置": IntentType.CUSTOM_PLAN,
        "建议": IntentType.CUSTOM_PLAN,

        "对比": IntentType.LOAN_COMPARE,
        "哪个好": IntentType.LOAN_COMPARE,

        # === 问候/感谢 ===
        "你好": IntentType.GREETING,
        "您好": IntentType.GREETING,
        "嗨": IntentType.GREETING,

        "谢谢": IntentType.THANKS,
        "感谢": IntentType.THANKS,
    }

    def recognize(self, query: str) -> Optional[IntentResult]:
        """识别意图，返回 None 表示未命中"""
        query_lower = query.lower()

        for keyword, intent in self.RULE_MAPPINGS.items():
            if keyword in query_lower:
                primary_category = IntentCategory.get_primary_category(intent)
                need_p0 = IntentCategory.is_p0_transfer(intent)

                return IntentResult(
                    intent=intent,
                    confidence=0.95,
                    reasoning=f"规则命中: 关键词 '{keyword}'",
                    source="rule",
                    primary_category=primary_category,
                    need_p0_transfer=need_p0
                )

        return None


class IntentRecognizer:
    """三级意图识别器 v1.1"""

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

        intent_list = "\n".join([f"- {i.value}: {i.name.replace('_', ' ')}" for i in IntentType])

        prompt = ChatPromptTemplate.from_template("""你是一个银行客服系统的意图识别器。

用户输入: {query}
{context}

请识别用户的意图，从以下类别中选择最匹配的（只能选择一个）：
{intent_list}

直接输出意图名称和置信度(0-1)，格式如下：
意图: xxx
置信度: 0.xx
分析: xxx""")

        response = llm.invoke(prompt.format(
            query=query,
            context=f"上下文: {context}" if context else "",
            intent_list=intent_list
        ))
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

        primary_category = IntentCategory.get_primary_category(intent)
        need_p0 = IntentCategory.is_p0_transfer(intent)

        return IntentResult(
            intent=intent,
            confidence=confidence,
            reasoning=f"LLM识别: {content[:100]}...",
            source="llm",
            primary_category=primary_category,
            need_p0_transfer=need_p0
        )


class SmartTriage:
    """智能分流模块 - 快速转人工决策"""

    def __init__(self):
        self.transfer_keywords = [
            "转人工", "人工服务", "真人", "客服",
            "要人工", "转接人工", "人工", "真人工"
        ]

        self.urgent_keywords = [
            "紧急", "快点", "急", "马上", "立刻",
            "快", "来不及了", "很急"
        ]

        self.risk_keywords = [
            "诈骗", "被骗", "钓鱼", "盗刷", "扣错",
            "冻结", "异常", "被盗", "风险"
        ]

    def should_transfer_immediately(self, query: str, history: List[dict],
                                   emotion_score: float = 0.0) -> Tuple[bool, str]:
        """
        判断是否需要立即转人工

        Returns:
            (是否立即转, 原因)
        """
        query_lower = query.lower()

        # P0: 明确要求转人工
        for keyword in self.transfer_keywords:
            if keyword in query_lower:
                return True, f"P0触发: 明确要求转人工（关键词: {keyword}）"

        # P0: 情绪激烈
        if emotion_score > 0.8:
            return True, f"P0触发: 用户情绪激烈（评分: {emotion_score}）"

        # P0: 紧急求助
        for keyword in self.urgent_keywords:
            if keyword in query_lower:
                return True, f"P0触发: 紧急求助（关键词: {keyword}）"

        # P0: 风险类
        for keyword in self.risk_keywords:
            if keyword in query_lower:
                return True, f"P0触发: 风险相关（关键词: {keyword}）"

        # P0: 历史对话中已连续要求转人工
        transfer_count = sum(1 for h in history if h.get("intent") == IntentType.HUMAN_SERVICE.value)
        if transfer_count >= 2:
            return True, f"P0触发: 连续{transfer_count}次要求转人工"

        # P1: 同一问题3轮未解决
        if len(history) >= 3:
            same_intent_count = 1
            last_intent = history[-1].get("intent") if history else None
            for h in history[-3:]:
                if h.get("intent") == last_intent:
                    same_intent_count += 1
            if same_intent_count >= 3 and not history[-1].get("resolved"):
                return True, "P1触发: 同一问题3轮未解决，建议转人工"

        return False, ""

    def generate_transfer_summary(self, history: List[dict],
                                 final_intent: IntentType) -> dict:
        """
        生成转人工摘要，供人工客服参考

        避免用户重复描述问题
        """
        # 提取用户问题
        user_queries = [h.get("query", "") for h in history if h.get("role") == "user"]

        # 提取AI回答摘要
        ai_summaries = []
        for h in history:
            if h.get("role") == "assistant":
                answer = h.get("answer", "")
                ai_summaries.append(answer[:100] + "..." if len(answer) > 100 else answer)

        # 统计意图分布
        intent_counts = {}
        for h in history:
            intent = h.get("intent", "unknown")
            intent_counts[intent] = intent_counts.get(intent, 0) + 1

        return {
            "user_main_query": user_queries[0] if user_queries else "",
            "conversation_turns": len(history),
            "final_intent": final_intent.value,
            "intent_distribution": intent_counts,
            "user_query_history": user_queries,
            "ai_answer_summaries": ai_summaries[-3:],  # 最近3轮
            "recommended_transfer_reason": f"意图分类: {final_intent.value}",
        }