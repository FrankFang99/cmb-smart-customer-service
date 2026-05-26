"""
瀹㈡湇 Agent 鏍稿績
鏁村悎鎰忓浘璇嗗埆銆丷AG 妫€绱€佸伐鍏疯皟鐢?"""
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
    """Agent 鍥炲缁撴瀯"""
    answer: str = Field(description="鍥炵瓟鍐呭")
    intent: str = Field(description="璇嗗埆鐨勬剰鍥?)
    confidence: float = Field(description="缃俊搴?)
    tool_used: Optional[str] = Field(description="浣跨敤鐨勫伐鍏?)
    sources: Optional[List[str]] = Field(description="鍙傝€冪殑鐭ヨ瘑鏉ユ簮")


class CustomerServiceAgent:
    """
    閾惰鏅鸿兘瀹㈡湇 Agent
    - 鎰忓浘璇嗗埆锛堥樁姊紡锛?    - 鐭ヨ瘑搴撴绱紙RAG锛?    - 宸ュ叿璋冪敤锛堟ā鎷熼摱琛屼笟鍔★級
    - 澶氳疆瀵硅瘽绠＄悊
    """

    def __init__(self, settings):
        self.settings = settings

        # 鍒濆鍖栫粍浠?        self.intent_recognizer = IntentRecognizer(settings)
        self.retriever = create_retriever(KNOWLEDGE_BASE, k=5)
        self.conversation_manager = ConversationManager(max_history=20)

        # 鍒濆鍖?LLM
        self.llm = ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            temperature=0.7
        )

        # 绯荤粺鎻愮ず璇?        self.system_prompt = """浣犳槸涓€涓笓涓氱殑鎷涘晢閾惰鏅鸿兘瀹㈡湇鍔╂墜銆?
浣犵殑鑱岃矗锛?1. 绀艰矊銆佷笓涓氬湴鍥炵瓟鐢ㄦ埛闂
2. 鏍规嵁鐢ㄦ埛鎰忓浘鎻愪緵鍑嗙‘鐨勪俊鎭拰甯姪
3. 褰撻渶瑕佹煡璇俊鎭椂锛屼娇鐢ㄦ彁渚涚殑宸ュ叿
4. 濮嬬粓淇濇寔鑰愬績鍜屽弸濂?
娉ㄦ剰浜嬮」锛?- 涓嶈娉勯湶浠讳綍鏁忔劅淇℃伅
- 涓嶈杩涜鐪熷疄鐨勪氦鏄撴搷浣?- 濡傛灉閬囧埌鏃犳硶瑙ｅ喅鐨勯棶棰橈紝閫傛椂寮曞鐢ㄦ埛杞汉宸ユ湇鍔?- 鍙娇鐢ㄤ互涓嬪伐鍏凤細check_balance, query_bill, search_branch, get_product_info, card_loss_report, transfer_guide, schedule_human_service"""

    def chat(self, user_input: str, session_id: str = "default") -> Dict:
        """
        澶勭悊鐢ㄦ埛杈撳叆
        """
        # 1. 娣诲姞鐢ㄦ埛娑堟伅
        self.conversation_manager.add_message(session_id, "user", user_input)

        # 2. 鎰忓浘璇嗗埆
        intent_result = self.intent_recognizer.recognize(user_input)
        self.conversation_manager.update_context(session_id, current_intent=intent_result.intent.value)

        # 3. 鏍规嵁鎰忓浘澶勭悊
        response = self._handle_by_intent(user_input, intent_result, session_id)

        # 4. 娣诲姞鍔╂墜娑堟伅
        self.conversation_manager.add_message(
            session_id,
            "assistant",
            response["answer"],
            metadata={"intent": intent_result.intent.value, "confidence": intent_result.confidence}
        )

        return response

    def _handle_by_intent(self, query: str, intent_result: IntentResult, session_id: str) -> Dict:
        """鏍规嵁鎰忓浘绫诲瀷澶勭悊璇锋眰"""

        # 杞汉宸?        if intent_result.intent == IntentType.HUMAN_SERVICE:
            return self._handle_human_service(session_id)

        # 鎶曡瘔
        if intent_result.intent == IntentType.COMPLAINT:
            return self._handle_complaint(query, session_id)

        # 鐭ヨ瘑搴撴煡璇紙FAQ銆佷骇鍝併€佺綉鐐圭瓑锛?        if intent_result.intent in [IntentType.FAQ, IntentType.ACCOUNT_QUERY,
                                     IntentType.BILL_QUERY, IntentType.BRANCH_QUERY,
                                     IntentType.PRODUCT_QUERY, IntentType.CARD_MANAGE,
                                     IntentType.TRANSFER_GUIDE]:
            return self._handle_knowledge_query(query, intent_result, session_id)

        # 闂€?        if intent_result.intent == IntentType.GREETING:
            return {
                "answer": "鎮ㄥソ锛佹垜鏄嫑鍟嗛摱琛屾櫤鑳藉鏈嶅皬鎷涳紝鏈変粈涔堝彲浠ュ府鎮紵\n\n鎮ㄥ彲浠ュ挩璇細\n- 璐︽埛浣欓鏌ヨ\n- 淇＄敤鍗¤处鍗昞n- 缃戠偣鏌ヨ\n- 鐞嗚储浜у搧\n- 杞处鎿嶄綔\n- 鍗＄墖绠＄悊绛?,
                "intent": intent_result.intent.value,
                "confidence": intent_result.confidence,
                "tool_used": None,
                "sources": []
            }

        # 鏈煡鎰忓浘 - RAG 妫€绱㈠厹搴?        return self._handle_rag_fallback(query, session_id)

    def _handle_human_service(self, session_id: str) -> Dict:
        """澶勭悊杞汉宸ヨ姹?""
        result = execute_tool("schedule_human_service", session_id=session_id)
        return {
            "answer": result.message,
            "intent": "human_service",
            "confidence": 1.0,
            "tool_used": "schedule_human_service",
            "sources": []
        }

    def _handle_complaint(self, query: str, session_id: str) -> Dict:
        """澶勭悊鎶曡瘔"""
        prompt = ChatPromptTemplate.from_template("""鐢ㄦ埛琛ㄨ揪浜嗕笉婊★紝璇峰厛琛ㄨ揪姝夋剰鍜岀悊瑙ｏ紝鐒跺悗锛?1. 璁ょ湡鍊惧惉骞惰褰曢棶棰?2. 鎻愪緵瑙ｅ喅鏂规鎴栧缓璁?3. 寮曞鐢ㄦ埛閫氳繃鍚堥€傛笭閬撳弽棣?
鐢ㄦ埛鍙嶉锛歿query}

璇风敤涓撲笟銆佸弸濂界殑鏂瑰紡鍥炲銆?"")

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
        鐭ヨ瘑搴撴煡璇?        缁撳悎 RAG 妫€绱?+ LLM 鐢熸垚
        """
        # RAG 妫€绱?        retrieval_results = self.retriever.retrieve(query, top_k=3)

        if retrieval_results and retrieval_results[0]["score"] > 0.5:
            # 鐩存帴浣跨敤妫€绱㈢粨鏋?            best_match = retrieval_results[0]
            answer = best_match["answer"]
            sources = [best_match["id"]]
            tool_used = None

            # 鍒ゆ柇鏄惁闇€瑕佽皟鐢ㄥ伐鍏?            if intent_result.intent == IntentType.ACCOUNT_QUERY and "浣欓" in query:
                result = execute_tool("check_balance", account_id="****1234")
                answer += f"\n\n{result.message}"
                tool_used = "check_balance"

            elif intent_result.intent == IntentType.BILL_QUERY and "璐﹀崟" in query:
                result = execute_tool("query_bill", card_id="****5678")
                answer += f"\n\n{result.message}"
                tool_used = "query_bill"

            elif intent_result.intent == IntentType.BRANCH_QUERY:
                result = execute_tool("search_branch", city="浣涘北")
                answer += f"\n\n{result.message}"
                tool_used = "search_branch"

            return {
                "answer": answer,
                "intent": intent_result.intent.value,
                "confidence": intent_result.confidence,
                "tool_used": tool_used,
                "sources": sources
            }

        # RAG 缁撴灉涓嶇悊鎯筹紝鐢?LLM 鍏滃簳
        return self._handle_rag_fallback(query, session_id)

    def _handle_rag_fallback(self, query: str, session_id: str) -> Dict:
        """RAG + LLM 铻嶅悎鐢熸垚"""
        # 鑾峰彇瀵硅瘽涓婁笅鏂?        context = self.conversation_manager.build_context_for_llm(
            session_id,
            system_prompt=self.system_prompt
        )

        # 妫€绱㈢浉鍏崇煡璇?        retrieval_results = self.retriever.retrieve(query, top_k=3)

        # 鏋勫缓鎻愮ず璇?        knowledge_context = "\n\n".join([
            f"銆愬弬鑰冪煡璇?{i+1}銆慭nID: {r['id']}\n闂: {r['question']}\n鍥炵瓟: {r['answer']}"
            for i, r in enumerate(retrieval_results)
        ]) if retrieval_results else "锛堟棤鐩稿叧鐭ヨ瘑锛?

        prompt = ChatPromptTemplate.from_template("""鍩轰簬浠ヤ笅淇℃伅锛屽洖绛旂敤鎴烽棶棰樸€?
銆愬璇濅笂涓嬫枃銆?{context}

銆愮敤鎴烽棶棰樸€?{query}

銆愮浉鍏崇煡璇嗐€?{knowledge}

璇风粨鍚堜笂涓嬫枃鍜岀浉鍏崇煡璇嗭紝缁欏嚭涓撲笟銆佸噯纭殑鍥炵瓟銆傚洖绛斿悗鏍囨敞鍙傝€冩潵婧愩€?"")

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
        """鑾峰彇浼氳瘽淇℃伅"""
        return self.conversation_manager.get_context_summary(session_id)