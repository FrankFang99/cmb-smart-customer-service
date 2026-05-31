"""
真实客服Agent接入层
将 CustomerServiceAgent 适配到评测框架
"""
import os
import sys
import time
import json
from typing import Dict, List, Optional

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.config import settings


class RealCustomerServiceAgent:
    """
    真实客服Agent - 接入DeepSeek API
    封装 CustomerServiceAgent 并适配评测框架接口
    """

    def __init__(self):
        """初始化真实Agent"""
        # 延迟导入避免循环依赖
        from src.agent.customer_service_agent import CustomerServiceAgent

        # 设置API Key
        if not settings.deepseek_api_key:
            raise ValueError("请在 .env 文件中设置 DEEPSEEK_API_KEY")

        # 初始化Agent
        self.agent = CustomerServiceAgent(settings)

        # 意图类型映射：v1.1 -> v1.0
        self.intent_mapping = {
            # 查询类
            "query_balance": "account_query",
            "query_bill": "bill_query",
            "query_bank_info": "branch_query",
            "query_progress": "branch_query",
            "query_other": "faq",

            # 交易操作类
            "transfer": "transfer_guide",
            "password_manage": "card_manage",
            "card_loss": "card_manage",
            "card_activate": "card_manage",
            "transaction_other": "card_manage",

            # 咨询类
            "consult_rate": "product_query",
            "consult_fee": "faq",
            "consult_rule": "faq",
            "consult_activity": "faq",
            "consult_product": "product_query",

            # 服务转接类
            "human_service": "human_service",
            "complaint": "complaint",
            "suggestion": "complaint",
            "urgent_help": "complaint",

            # 营销咨询类
            "marketing_wealth": "product_query",
            "marketing_credit": "product_query",
            "marketing_loan": "product_query",
            "marketing_promo": "faq",

            # 风险类
            "anti_fraud": "complaint",
            "theft_report": "complaint",
            "freeze_request": "complaint",
            "security_event": "complaint",

            # 复杂需求
            "custom_plan": "product_query",
            "loan_compare": "product_query",
            "complex_business": "faq",
            "human_intervention": "human_service",

            # 模糊/无效
            "accidental_touch": "greeting",
            "semantic_invalid": "faq",
            "unknown": "faq",

            # 系统意图
            "greeting": "greeting",
            "thanks": "greeting",
        }

    def process(self, question: str, context: Optional[Dict] = None) -> Dict:
        """
        处理用户问题 - 适配评测框架接口

        Returns:
            {
                "intent": str,           # v1.1 意图类型
                "confidence": float,
                "answer": str,
                "transfer": bool,
                "priority": Optional[str],
                "needs_risk_disclosure": bool,
                "latency_ms": float
            }
        """
        start_time = time.time()

        # 调用真实Agent
        try:
            response = self.agent.chat(question, session_id="eval_session")

            # 获取v1.0意图
            v1_intent = response.get("intent", "faq")

            # 映射到v1.1意图
            v1_1_intent = self._map_intent_v1_to_v1_1(v1_intent)

            # 判断是否需要转人工
            transfer = self._should_transfer(v1_1_intent)

            # 判断优先级
            priority = "P0" if transfer and v1_1_intent in [
                "human_service", "complaint", "urgent_help",
                "anti_fraud", "theft_report", "freeze_request"
            ] else None

            # 判断是否需要风险提示
            needs_risk = v1_1_intent in [
                "marketing_wealth", "marketing_loan", "consult_rate",
                "consult_product", "custom_plan", "loan_compare"
            ]

            latency = (time.time() - start_time) * 1000

            return {
                "intent": v1_1_intent,
                "confidence": response.get("confidence", 0.7),
                "answer": response.get("answer", ""),
                "transfer": transfer,
                "priority": priority,
                "needs_risk_disclosure": needs_risk,
                "latency_ms": latency
            }

        except Exception as e:
            # 错误处理
            latency = (time.time() - start_time) * 1000
            return {
                "intent": "unknown",
                "confidence": 0.0,
                "answer": f"抱歉，系统处理出现错误：{str(e)}",
                "transfer": False,
                "priority": None,
                "needs_risk_disclosure": False,
                "latency_ms": latency,
                "error": str(e)
            }

    def _map_intent_v1_to_v1_1(self, v1_intent: str) -> str:
        """将v1.0意图映射到v1.1"""
        # 直接映射
        if v1_intent in self.intent_mapping:
            return self.intent_mapping[v1_intent]

        # 根据关键词推断
        return v1_intent

    def _should_transfer(self, intent: str) -> bool:
        """判断是否需要转人工"""
        return intent in [
            "human_service", "complaint", "urgent_help",
            "anti_fraud", "theft_report", "freeze_request",
            "suggestion", "custom_plan", "loan_compare",
            "complex_business", "human_intervention"
        ]


def create_agent() -> RealCustomerServiceAgent:
    """创建真实Agent实例"""
    return RealCustomerServiceAgent()


# 测试函数
if __name__ == "__main__":
    print("测试真实Agent...")

    agent = create_agent()

    test_questions = [
        "我卡里还有多少钱",
        "转人工",
        "有什么理财产品",
        "卡丢了怎么办",
    ]

    for q in test_questions:
        print(f"\n问题: {q}")
        result = agent.process(q)
        print(f"意图: {result['intent']}")
        print(f"置信度: {result['confidence']}")
        print(f"转人工: {result['transfer']}")
        print(f"回答: {result['answer'][:100]}...")