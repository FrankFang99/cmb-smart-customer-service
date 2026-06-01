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
    真实客服Agent - 接入MiniMax API
    封装 CustomerServiceAgent 并适配评测框架接口
    """

    def __init__(self):
        """初始化真实Agent"""
        # 延迟导入避免循环依赖
        from src.agent.customer_service_agent import CustomerServiceAgent

        # 检查API Key - 优先MiniMax
        api_key, base_url, provider = settings.get_active_api_key()
        if not api_key:
            raise ValueError("请在 .env 文件中设置 MINIMAX_API_KEY 或 DEEPSEEK_API_KEY")

        print(f"使用 {provider} API")
        
        # 初始化Agent
        self.agent = CustomerServiceAgent(settings)

        # 意图类型映射：v2.0 -> 评测用简化类型
        self.intent_mapping = {
            # INFO - 信息查询类
            "info_acc_balance": "account_query",
            "info_acc_detail": "account_query",
            "info_acc_status": "account_query",
            "info_acc_info": "account_query",
            "info_bill_amount": "bill_query",
            "info_bill_date": "bill_query",
            "info_bill_min": "bill_query",
            "info_bill_point": "bill_query",
            "info_tran_record": "account_query",
            "info_tran_status": "account_query",
            "info_prod_wealth": "product_query",
            "info_prod_loan": "product_query",
            "info_prod_credit": "product_query",
            "info_prog_application": "branch_query",
            "info_prog_transfer": "branch_query",
            "info_branch": "branch_query",
            "info_phone": "branch_query",
            "info_hour": "branch_query",
            "info_other": "faq",

            # BIZ - 业务办理类
            "biz_tran_internal": "transfer_guide",
            "biz_tran_external": "transfer_guide",
            "biz_tran_remit": "transfer_guide",
            "biz_tran_reverse": "transfer_guide",
            "biz_tran_limit": "faq",
            "biz_card_loss": "card_manage",
            "biz_card_activate": "card_manage",
            "biz_card_reissue": "card_manage",
            "biz_card_damage": "card_manage",
            "biz_card_eject": "card_manage",
            "biz_card_cancel": "card_manage",
            "biz_pwd_reset": "card_manage",
            "biz_pwd_change": "card_manage",
            "biz_pwd_set": "card_manage",
            "biz_pay_repay": "faq",
            "biz_pay_autopay": "faq",
            "biz_pay_overdue": "faq",
            "biz_installment": "product_query",
            "biz_other": "faq",

            # CONSULT - 咨询投诉类
            "cons_prod_wealth": "product_query",
            "cons_prod_loan": "product_query",
            "cons_prod_credit": "product_query",
            "cons_prod_deposit": "product_query",
            "cons_prod_compare": "product_query",
            "cons_fee_tran": "faq",
            "cons_fee_withdrw": "faq",
            "cons_fee_install": "faq",
            "cons_fee_other": "faq",
            "cons_rule_refund": "faq",
            "cons_rule_cancel": "faq",
            "cons_rule_overdue": "faq",
            "cons_rule_other": "faq",
            "cons_comp_service": "complaint",
            "cons_comp_delay": "complaint",
            "cons_comp_error": "complaint",
            "cons_comp_refuse": "complaint",
            "cons_comp_other": "complaint",
            "cons_sugg_improve": "complaint",
            "cons_sugg_new": "complaint",
            "cons_urg_loss": "complaint",
            "cons_urg_lock": "complaint",
            "cons_urg_card": "complaint",
            "cons_urg_human": "human_service",

            # SALES - 营销推广类
            "sales_wealth_prod": "product_query",
            "sales_wealth_return": "product_query",
            "sales_wealth_risk": "product_query",
            "sales_loan_prod": "product_query",
            "sales_loan_rate": "product_query",
            "sales_loan_cond": "product_query",
            "sales_credit_prod": "product_query",
            "sales_credit_point": "product_query",
            "sales_credit_fee": "product_query",
            "sales_promo_discount": "faq",
            "sales_promo_reward": "faq",
            "sales_promo_other": "faq",

            # SECURITY - 安全风控类 [全部P0]
            "sec_fraud_report": "complaint",
            "sec_fraud_suspect": "complaint",
            "sec_fraud_phishing": "complaint",
            "sec_fraud_scam": "complaint",
            "sec_stolen_card": "complaint",
            "sec_stolen_info": "complaint",
            "sec_freeze_unexpected": "complaint",
            "sec_freeze_request": "complaint",
            "sec_freeze_legal": "complaint",
            "sec_virus": "complaint",
            "sec_hack": "complaint",
            "sec_other": "complaint",

            # SYSTEM - 系统交互类
            "sys_greeting": "greeting",
            "sys_bye": "greeting",
            "sys_intro": "greeting",
            "sys_thanks": "greeting",
            "sys_feedback": "greeting",
            "sys_invalid": "faq",
            "sys_gibberish": "faq",
            "sys_offtopic": "faq",
            "sys_confirm": "faq",
            "sys_repeat": "faq",
            "sys_other": "faq",
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