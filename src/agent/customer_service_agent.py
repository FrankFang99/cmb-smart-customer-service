"""
客服 Agent 核心
整合意图识别、RAG 检索、工具调用
"""
from typing import Dict, List, Optional
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

from ..components.intent_recognizer import IntentRecognizer, IntentType, IntentResult
from ..rag.knowledge_base import KNOWLEDGE_BASE, get_knowledge_by_intent
from ..rag.retriever import create_retriever, HybridRetriever
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
        self.retriever = create_retriever(KNOWLEDGE_BASE, k=5)
        self.conversation_manager = ConversationManager(max_history=20)

        # 初始化 LLM
        self.llm = ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
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

        # 转人工
        if intent_result.intent == IntentType.HUMAN_SERVICE:
            return self._handle_human_service(session_id)

        # 投诉
        if intent_result.intent == IntentType.COMPLAINT:
            return self._handle_complaint(query, session_id)

        # 知识库查询（FAQ、产品、网点等）
        if intent_result.intent in [IntentType.FAQ, IntentType.ACCOUNT_QUERY,
                                     IntentType.BILL_QUERY, IntentType.BRANCH_QUERY,
                                     IntentType.PRODUCT_QUERY, IntentType.CARD_MANAGE,
                                     IntentType.TRANSFER_GUIDE]:
            return self._handle_knowledge_query(query, intent_result, session_id)

        # 问候
        if intent_result.intent == IntentType.GREETING:
            return {
                "answer": "您好！我是招商银行智能客服小招，有什么可以帮您？\n\n您可以咨询：\n- 账户余额查询\n- 信用卡账单\n- 网点查询\n- 理财产品\n- 转账操作\n- 卡片管理等",
                "intent": intent_result.intent.value,
                "confidence": intent_result.confidence,
                "tool_used": None,
                "sources": []
            }

        # 未知意图 - RAG 检索兜底
        return self._handle_rag_fallback(query, session_id)

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
3. 引导用户通过合适渠道反馈

用户反馈：{query}

请用专业、友好的方式回复。""")

        response = self.llm.invoke(prompt.format(query=query))
        return {
            "answer": response.content,
            "intent": "complaint",
            "confidence": 0.9,
            "tool_used": None,
            "sources": ["complaint_handling_guide"]
        }

    def _handle_knowledge_query(self, query: str, intent_result: IntentResult, session_id: str) -> Dict:
        """
        知识库查询
        结合 RAG 检索 + LLM 生成
        """
        # RAG 检索
        retrieval_results = self.retriever.retrieve(query, top_k=3)

        if retrieval_results and retrieval_results[0]["score"] > 0.5:
            # 直接使用检索结果
            best_match = retrieval_results[0]
            answer = best_match["answer"]
            sources = [best_match["id"]]
            tool_used = None

            # 判断是否需要调用工具
            if intent_result.intent == IntentType.ACCOUNT_QUERY and "余额" in query:
                result = execute_tool("check_balance", account_id="****1234")
                answer += f"\n\n{result.message}"
                tool_used = "check_balance"

            elif intent_result.intent == IntentType.BILL_QUERY and "账单" in query:
                result = execute_tool("query_bill", card_id="****5678")
                answer += f"\n\n{result.message}"
                tool_used = "query_bill"

            elif intent_result.intent == IntentType.BRANCH_QUERY:
                result = execute_tool("search_branch", city="佛山")
                answer += f"\n\n{result.message}"
                tool_used = "search_branch"

            return {
                "answer": answer,
                "intent": intent_result.intent.value,
                "confidence": intent_result.confidence,
                "tool_used": tool_used,
                "sources": sources
            }

        # RAG 结果不理想，用 LLM 兜底
        return self._handle_rag_fallback(query, session_id)

    def _handle_rag_fallback(self, query: str, session_id: str) -> Dict:
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
            "intent": "rag_fallback",
            "confidence": 0.6,
            "tool_used": None,
            "sources": [r["id"] for r in retrieval_results] if retrieval_results else []
        }

    def get_session_info(self, session_id: str) -> Dict:
        """获取会话信息"""
        return self.conversation_manager.get_context_summary(session_id)