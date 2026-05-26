"""
闃舵寮忔剰鍥捐瘑鍒櫒
瑙勫垯 -> 杞婚噺妯″瀷 -> LLM 涓夌骇鍥為€€
"""
from enum import Enum
from typing import Optional, Tuple
from dataclasses import dataclass


class IntentType(str, Enum):
    """閾惰瀹㈡湇鎰忓浘绫诲瀷"""
    GREETING = "greeting"                    # 闂€?    FAQ = "faq"                             # 甯歌闂鍜ㄨ
    ACCOUNT_QUERY = "account_query"         # 璐︽埛鏌ヨ
    BILL_QUERY = "bill_query"               # 璐﹀崟鏌ヨ
    BRANCH_QUERY = "branch_query"           # 缃戠偣鏌ヨ
    COMPLAINT = "complaint"                # 鎶曡瘔
    TRANSFER_GUIDE = "transfer_guide"      # 杞处鎸囧紩
    PRODUCT_QUERY = "product_query"        # 浜у搧鍜ㄨ
    CARD_MANAGE = "card_manage"            # 鍗＄墖绠＄悊
    HUMAN_SERVICE = "human_service"        # 杞汉宸?    UNKNOWN = "unknown"                    # 鏈煡


@dataclass
class IntentResult:
    """鎰忓浘璇嗗埆缁撴灉"""
    intent: IntentType
    confidence: float
    reasoning: str
    source: str  # "rule" | "model" | "llm"


class RuleBasedRecognizer:
    """瑙勫垯寮曟搸 - 澶勭悊楂橀鎸囦护"""

    # 楂橀鍏抽敭璇?-> 鎰忓浘鏄犲皠
    RULE_MAPPINGS = {
        # 杞汉宸?        "杞汉宸?: IntentType.HUMAN_SERVICE,
        "浜哄伐鏈嶅姟": IntentType.HUMAN_SERVICE,
        "鐪熶汉": IntentType.HUMAN_SERVICE,
        "瀹㈡湇": IntentType.HUMAN_SERVICE,
        "甯垜杞?: IntentType.HUMAN_SERVICE,

        # 璐︽埛鏌ヨ
        "浣欓": IntentType.ACCOUNT_QUERY,
        "璐︽埛": IntentType.ACCOUNT_QUERY,
        "澶氬皯閽?: IntentType.ACCOUNT_QUERY,

        # 璐﹀崟
        "璐﹀崟": IntentType.BILL_QUERY,
        "杩樻": IntentType.BILL_QUERY,
        "娑堣垂": IntentType.BILL_QUERY,

        # 缃戠偣
        "缃戠偣": IntentType.BRANCH_QUERY,
        "鍒嗚": IntentType.BRANCH_QUERY,
        "鏀": IntentType.BRANCH_QUERY,
        "鍦ㄥ摢閲?: IntentType.BRANCH_QUERY,
        "鍦板潃": IntentType.BRANCH_QUERY,

        # 鎶曡瘔
        "鎶曡瘔": IntentType.COMPLAINT,
        "涓嶆弧": IntentType.COMPLAINT,
        "澶樊": IntentType.COMPLAINT,
        "鍙嶉": IntentType.COMPLAINT,

        # 杞处
        "杞处": IntentType.TRANSFER_GUIDE,
        "姹囨": IntentType.TRANSFER_GUIDE,

        # 浜у搧
        "鐞嗚储": IntentType.PRODUCT_QUERY,
        "瀛樻": IntentType.PRODUCT_QUERY,
        "璐锋": IntentType.PRODUCT_QUERY,

        # 鍗＄墖绠＄悊
        "鎸傚け": IntentType.CARD_MANAGE,
        "琛ュ崱": IntentType.CARD_MANAGE,
        "瀵嗙爜": IntentType.CARD_MANAGE,
    }

    def recognize(self, query: str) -> Optional[IntentResult]:
        """璇嗗埆鎰忓浘锛岃繑鍥?None 琛ㄧず鏈懡涓?""
        query_lower = query.lower()

        for keyword, intent in self.RULE_MAPPINGS.items():
            if keyword in query_lower:
                return IntentResult(
                    intent=intent,
                    confidence=0.95,
                    reasoning=f"瑙勫垯鍛戒腑: 鍏抽敭璇?'{keyword}'",
                    source="rule"
                )

        return None


class IntentRecognizer:
    """涓夌骇鎰忓浘璇嗗埆鍣?""

    def __init__(self, settings):
        self.settings = settings
        self.rule_engine = RuleBasedRecognizer()

    def recognize(self, query: str, context: Optional[dict] = None) -> IntentResult:
        """
        闃舵寮忔剰鍥捐瘑鍒?
        娴佺▼: 瑙勫垯 -> 杞婚噺妯″瀷 -> LLM
        """
        # 绗竴灞傦細瑙勫垯寮曟搸
        result = self.rule_engine.recognize(query)
        if result and result.confidence >= self.settings.rule_confidence_threshold:
            return result

        # 绗簩灞傦細杞婚噺妯″瀷锛堝緟鎺ュ叆 sentence-transformers锛?        # result = self.lightweight_model.predict(query)
        # if result and result.confidence >= self.settings.model_confidence_threshold:
        #     return result

        # 绗笁灞傦細LLM 鍏滃簳
        return self._llm_fallback(query, context)

    def _llm_fallback(self, query: str, context: Optional[dict] = None) -> IntentResult:
        """LLM 鎰忓浘瑙ｆ瀽"""
        from langchain_openai import ChatOpenAI
        from langchain.prompts import ChatPromptTemplate

        llm = ChatOpenAI(
            model=self.settings.llm_model,
            api_key=self.settings.deepseek_api_key,
            base_url=self.settings.deepseek_base_url,
            temperature=0.1
        )

        prompt = ChatPromptTemplate.from_template("""浣犳槸涓€涓摱琛屽鏈嶇郴缁熺殑鎰忓浘璇嗗埆鍣ㄣ€?
鐢ㄦ埛杈撳叆: {query}
{context}

璇疯瘑鍒敤鎴风殑鎰忓浘锛屼粠浠ヤ笅绫诲埆涓€夋嫨鏈€鍖归厤鐨?
- greeting: 闂€?- faq: 甯歌闂鍜ㄨ
- account_query: 璐︽埛鏌ヨ
- bill_query: 璐﹀崟鏌ヨ
- branch_query: 缃戠偣鏌ヨ
- complaint: 鎶曡瘔
- transfer_guide: 杞处鎸囧紩
- product_query: 浜у搧鍜ㄨ
- card_manage: 鍗＄墖绠＄悊
- human_service: 杞汉宸?
鐩存帴杈撳嚭鎰忓浘鍚嶇О鍜岀疆淇″害(0-1)锛屾牸寮忓涓?
鎰忓浘: xxx
缃俊搴? 0.xx
鍒嗘瀽: xxx""")

        response = llm.invoke(prompt.format(query=query, context=f"涓婁笅鏂? {context}" if context else ""))
        content = response.content

        # 瑙ｆ瀽 LLM 杩斿洖
        lines = content.split('\n')
        intent_str = ""
        confidence = 0.5

        for line in lines:
            if line.startswith("鎰忓浘:"):
                intent_str = line.replace("鎰忓浘:", "").strip()
            if line.startswith("缃俊搴?"):
                try:
                    confidence = float(line.replace("缃俊搴?", "").strip())
                except:
                    confidence = 0.6

        # 鏄犲皠鍒?IntentType
        intent_map = {e.value: e for e in IntentType}
        intent = intent_map.get(intent_str.lower(), IntentType.UNKNOWN)

        return IntentResult(
            intent=intent,
            confidence=confidence,
            reasoning=f"LLM璇嗗埆: {content[:100]}...",
            source="llm"
        )