"""
客服 Agent 核心
整合意图识别、RAG 检索、工具调用
"""
from typing import Dict, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

from ..components.intent_recognizer import IntentRecognizer, IntentType, IntentResult
from ..rag.knowledge_base import KNOWLEDGE_BASE, get_knowledge_by_intent
from .conversation_manager import ConversationManager
from .tools import execute_tool, BANKING_TOOLS, ToolResult


class AgentResponse(BaseModel):
    """Agent 回复结构"""
    answer: str = Field(description="回答内容")
    intent: str = Field(description="识别的意图")
    confidence: float = Field(description="置信度")
    tool_used: Optional[str] = Field(description="使用的工具")
    sources: Optional[List[str]] = Field(description="参考的知识来源")


class CustomerServiceAgent:
    """
    银行智能客服 Agent
    - 意图识别（阶梯式）
    - 知识库检索（RAG）
    - 工具调用（模拟银行业务）
    - 多轮对话管理
    """

    def __init__(self, settings):
        self.settings = settings

        # 初始化组件
        self.intent_recognizer = IntentRecognizer(settings)

        # 使用简单检索器（不依赖外部模型）
        try:
            from ..rag.simple_retriever import create_retriever
            self.retriever = create_retriever(KNOWLEDGE_BASE, k=5)
        except ImportError:
            # 完全无法创建检索器，使用空列表
            self.retriever = None

        self.conversation_manager = ConversationManager(max_history=20)

        # 初始化 LLM - 优先使用 MiniMax
        api_key, base_url, provider = settings.get_active_api_key()
        if not api_key:
            raise ValueError("请在 .env 文件中设置 MINIMAX_API_KEY 或 DEEPSEEK_API_KEY")
        
        # 根据 provider 选择 base URL
        if provider == "MiniMax":
            base_url = "https://api.minimaxi.com/v1"
        
        self.llm = ChatOpenAI(
            model="MiniMax-M2.7",
            api_key=api_key,
            base_url=base_url,
            temperature=0.7
        )

        # 系统提示词
        self.system_prompt = """你是一个专业的招商银行智能客服助手。

你的职责：
1. 礼貌、专业地回答用户问题
2. 根据用户意图提供准确的信息和帮助
3. 当需要查询信息时，使用提供的工具
4. 始终保持耐心和友好

注意事项：
- 不要泄露任何敏感信息
- 不要进行真实的交易操作
- 如果遇到无法解决的问题，适时引导用户转人工服务
- 只使用以下工具：check_balance, query_bill, search_branch, get_product_info, card_loss_report, transfer_guide, schedule_human_service"""

    def chat(self, user_input: str, session_id: str = "default") -> Dict:
        """
        处理用户输入
        """
        # 1. 添加用户消息
        self.conversation_manager.add_message(session_id, "user", user_input)

        # 2. 意图识别
        intent_result = self.intent_recognizer.recognize(user_input)
        self.conversation_manager.update_context(session_id, current_intent=intent_result.intent.value)

        # 3. 根据意图处理
        response = self._handle_by_intent(user_input, intent_result, session_id)

        # 4. 添加助手消息
        self.conversation_manager.add_message(
            session_id,
            "assistant",
            response["answer"],
            metadata={"intent": intent_result.intent.value, "confidence": intent_result.confidence}
        )

        return response

    def _handle_by_intent(self, query: str, intent_result: IntentResult, session_id: str) -> Dict:
        """根据意图类型处理请求"""
        intent = intent_result.intent

        # 转人工 - CONS_URG_HUMAN
        if intent == IntentType.CONS_URG_HUMAN:
            return self._handle_human_service(session_id)

        # 紧急类 - 转人工
        if intent in [IntentType.CONS_URG_LOSS, IntentType.CONS_URG_LOCK, IntentType.CONS_URG_CARD]:
            return self._handle_human_service(session_id)

        # 投诉类 - CONS_COMP
        if intent in [IntentType.CONS_COMP_SERVICE, IntentType.CONS_COMP_DELAY,
                      IntentType.CONS_COMP_ERROR, IntentType.CONS_COMP_REFUSE, IntentType.CONS_COMP_OTHER]:
            return self._handle_complaint(query, session_id)

        # 风险类 - SEC_ 开头的全部转人工
        if intent.value.startswith("sec_"):
            return self._handle_human_service(session_id)

        # 复杂需求 - 建议转人工
        if intent in [IntentType.CONS_PROD_COMPARE, IntentType.SALES_LOAN_RATE,
                      IntentType.SALES_LOAN_COND]:
            return self._handle_human_service(session_id)

        # 知识库查询（查询类、交易操作类、咨询类、营销咨询类）
        if intent.value.startswith(('info_', 'biz_', 'cons_', 'sales_')):
            # info_类优先用模板快速回答
            if intent.value.startswith("info_") and intent.value in self._get_info_templates():
                return self._handle_info_template(intent.value)
            # biz_简单业务类用模板
            if intent.value in self._get_biz_templates():
                return self._handle_biz_template(intent.value)
            # cons_和sales_类调LLM
            if intent.value.startswith(('cons_', 'sales_')):
                return self._handle_rag_fallback(query, intent_result, session_id)
            # 其他biz_类调LLM
            return self._handle_rag_fallback(query, intent_result, session_id)

        # 问候
        if intent in [IntentType.SYS_GREETING, IntentType.SYS_THANKS, IntentType.SYS_BYE]:
            return {
                "answer": "您好！我是招商银行智能客服小招，有什么可以帮您？\n\n您可以咨询：\n- 账户余额查询\n- 信用卡账单\n- 网点查询\n- 理财产品\n- 转账操作\n- 卡片管理等",
                "intent": intent_result.intent.value,
                "confidence": intent_result.confidence,
                "tool_used": None,
                "sources": []
            }

        # 未知意图 - RAG 检索兜底
        return self._handle_rag_fallback(query, intent_result, session_id)

    def _handle_info_template(self, intent: str) -> Dict:
        """信息查询类 - 用模板快速回答，不调LLM"""
        templates = self._get_info_templates()
        answer = templates.get(intent, "请您登录招商银行App或拨打95555查询相关信息。")
        
        return {
            "answer": answer,
            "intent": intent,
            "confidence": 0.95,
            "tool_used": None,
            "sources": []
        }
    
    def _get_info_templates(self) -> Dict:
        """获取信息查询模板字典"""
        return {
            "info_acc_balance": "您可以登录招商银行App或网上银行，点击「账户余额」查看当前余额。如需查询明细，请点击「交易明细」。如有疑问可拨打95555。",
            "info_bill_amount": "您可以登录招商银行App，点击「信用卡」→「账单查询」查看本期账单金额。也可以发送短信「ZD#卡号后四位」到95555查询。",
            "info_bill_date": "您的信用卡还款日可在App的「账单查询」中查看。还款日通常在账单日后的18-20天，请确保在还款日前还清。",
            "info_bill_min": "最低还款额会在每期账单中显示，一般为当月消费金额的10%左右。建议全额还款以避免产生利息。",
            "info_bill_point": "您的信用卡积分可在App「我的」→「积分」中查询。积分可兑换礼品、航空里程等，1积分约等于0.001元。",
            "info_tran_record": "您可以在App「交易明细」中查询近3年的交易记录，也可以设置交易提醒，实时掌握账户变动。",
            "info_branch": "招商银行网点信息请拨打95555或登录官网查询。您也可以使用App内的「网点查询」功能，查看附近网点及实时排队情况。",
            "info_hour": "招商银行网点营业时间一般为工作日9:00-17:00，周末部分网点营业。具体以各网点公告为准，建议提前电话确认。",
            "info_phone": "招商银行客服热线：95555。信用卡客服：400-880-5535。如有紧急情况可随时拨打。",
            "info_prog_application": "您可通过App「申请进度」查询您的业务办理进度，或拨打95555人工查询。",
            "info_prog_transfer": "同行转账通常即时到账，跨行转账一般1-2个工作日到账。如超过3个工作日未到账，请联系转出行核实。",
        }
    
    def _handle_biz_template(self, intent: str) -> Dict:
        """简单业务办理类 - 用模板快速回答"""
        templates = self._get_biz_templates()
        answer = templates.get(intent, "该业务建议您登录招商银行App操作，或拨打95555人工协助。")
        
        return {
            "answer": answer,
            "intent": intent,
            "confidence": 0.95,
            "tool_used": None,
            "sources": []
        }
    
    def _get_biz_templates(self) -> Dict:
        """获取业务办理模板字典"""
        return {
            "biz_card_activate": "卡片激活请登录招商银行App，点击「卡片管理」→「卡片激活」，按提示完成激活。也可以拨打卡背面的客服电话激活。",
            "biz_card_reissue": "补办新卡请携带身份证到就近招商银行网点办理，或登录App「卡片管理」→「补办新卡」申请，卡片将邮寄到您指定地址。",
            "biz_installment": "分期业务请登录App「信用卡」→「分期付款」申请，或拨打400-880-5535办理。分期费率请以申请页面显示为准。",
            "biz_pay_autopay": "自动还款设置请登录App「信用卡」→「自动还款设置」，绑定您的借记卡账户即可。设置后每月的到期还款日会自动扣款。",
        }
    
    def _handle_human_service(self, session_id: str) -> Dict:
        """处理转人工请求"""
        result = execute_tool("schedule_human_service", session_id=session_id)
        return {
            "answer": result.message,
            "intent": "human_service",
            "confidence": 1.0,
            "tool_used": "schedule_human_service",
            "sources": []
        }

    def _handle_complaint(self, query: str, session_id: str) -> Dict:
        """处理投诉"""
        prompt = ChatPromptTemplate.from_template("""用户表达了不满，请先表达歉意和理解，然后：
1. 认真倾听并记录问题
2. 提供解决方案或建议
3. 如需转人工，配合安排

用户问题：{query}""")

        response = self.llm.invoke(prompt.format(query=query))

        return {
            "answer": response.content,
            "intent": "complaint",
            "confidence": 0.8,
            "tool_used": None,
            "sources": []
        }

    def _handle_rag_fallback(self, query: str, intent_result: IntentResult, session_id: str) -> Dict:
        """RAG + LLM 融合生成"""
        # 获取对话上下文
        context = self.conversation_manager.build_context_for_llm(
            session_id,
            system_prompt=self.system_prompt
        )

        # 检索相关知识
        retrieval_results = self.retriever.retrieve(query, top_k=3)

        # 构建提示词
        knowledge_context = "\n\n".join([
            f"【参考知识 {i+1}】\nID: {r['id']}\n问题: {r['question']}\n回答: {r['answer']}"
            for i, r in enumerate(retrieval_results)
        ]) if retrieval_results else "（无相关知识）"

        prompt = ChatPromptTemplate.from_template("""基于以下信息，回答用户问题。

【对话上下文】
{context}

【用户问题】
{query}

【相关知识】
{knowledge}

请结合上下文和相关知识，给出专业、准确的回答。回答后标注参考来源。""")

        response = self.llm.invoke(prompt.format(
            context=context,
            query=query,
            knowledge=knowledge_context
        ))

        return {
            "answer": response.content,
            "intent": intent_result.intent.value,
            "confidence": 0.6,
            "tool_used": None,
            "sources": [r["id"] for r in retrieval_results] if retrieval_results else []
        }

    def get_session_info(self, session_id: str) -> Dict:
        """获取会话信息"""
        return self.conversation_manager.get_context_summary(session_id)