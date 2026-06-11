"""
业务端到端 Pipeline v3.3.8
============================

完整业务流: 用户输入 -> 意图识别 -> L0 红线 -> 槽位/上下文 -> RAG 4 阶段检索 -> LLM 生成 -> 回复

业界对应 (2024-2026 主流 Agent 架构):
- LangGraph / LangChain LCEL (LangChain)
- LlamaIndex QueryEngine (LlamaIndex)
- Haystack Pipeline (deepset)
- AWS Bedrock Agent / Azure AI Agent (云大厂)

本项目 0 依赖 LangChain, 自己组装, 业务定制更灵活

组件:
- IntentRecognizer (意图识别 17 级规则)
- check_l0 (L0 红线 268 词词典)
- RerankedRetriever (RAG 4 阶段: Sparse + Dense + MultiQuery + Rerank)
- minimax_client.chat (LLM 调用, 订阅 Key + api.minimaxi.com)

用法:
    from src.agent.e2e_pipeline import E2EPipeline
    p = E2EPipeline()
    result = p.handle("我信用卡被盗刷了", session_id="s1")
    print(result['answer'], result['action'])
"""
from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Any


# 确保项目根目录在 sys.path
_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


from src.components.intent_recognizer import IntentRecognizer
from src.eval.banking_l0_dict import check_l0
from src.rag.knowledge_base import KNOWLEDGE_BASE
from src.rag.reranker import create_reranked_retriever
from src.llm.minimax_client import chat as llm_chat
from src.agent.conversation_manager import ConversationManager


# ============================================================
# 业务回复模板 (L0 触发时不调 LLM, 银行业强约束)
# ============================================================
L0_RESPONSE_TEMPLATES = {
    "fraud_high_risk": (
        "您的问题涉及账户安全（疑似盗刷/被骗）。我已为您转接 95555 客服专员，"
        "请保持电话畅通。同时切记：银行工作人员不会向您索要密码、验证码或要求转账。"
        "如有可疑情况请立即拨打 110 报警。"
    ),
    "fraud_fake_official": (
        "您的问题涉及假冒公检法/银监会/银行等诈骗信号。我已为您转接 95555 客服专员，"
        "切记：银行不会通过电话/短信索要您的密码或要求您转账到所谓\"安全账户\"。"
    ),
    "fraud_investment": (
        "您的问题涉及高息/保本/稳赚等可疑投资信号。银行业务中任何承诺保本高收益的"
        "投资都不合规。我已为您转接 95555 客服专员核实。"
    ),
    "fraud_transfer": (
        "您的问题涉及给陌生人转账的预警。我已为您转接 95555 客服专员，"
        "请勿向陌生人转账。"
    ),
    "aml_large": (
        "您的问题涉及大额转账。我行已按规定上报此笔交易，客服专员将协助您完成合规手续。"
    ),
    "aml_structured": (
        "您的问题涉及分笔转账（化整为零）。该行为违反反洗钱法律法规，"
        "我已为您转接 95555 客服专员并上报合规。"
    ),
    "unauthorized_proxy_query": (
        "按银行规定，账户查询和操作需由账户本人办理。请账户本人持身份证到任一"
        "招商银行网点办理，或通过本人手机银行操作。"
    ),
    "unauthorized_proxy_transaction": (
        "按银行规定，业务代办需账户本人授权。请账户本人到任一招商银行网点"
        "办理委托授权手续。"
    ),
    "default": (
        "您的问题涉及账户安全和合规事项。我已为您转接 95555 客服专员处理。"
    ),
}


# ============================================================
# E2E Pipeline 主体
# ============================================================
class E2EPipeline:
    """
    银行业智能客服端到端 Pipeline

    流程:
    1. 意图识别 (规则 17 级, 0 依赖)
    2. L0 红线检测 (268 词词典, 银行业强约束)
       - 触发 -> 不调 LLM, 返回标准话术 + 转人工
       - 不触发 -> 继续
    3. RAG 4 阶段检索 (Sparse + Dense + MultiQuery + Rerank)
    4. 业务 context 拼装
    5. LLM 生成回答
    6. 返回结果

    输入: {user_input, session_id, history (optional)}
    输出: {answer, intent, action, l0_triggered, sources, elapsed_ms, ...}
    """

    def __init__(self, k: int = 3):
        """
        Args:
            k: RAG 检索 top_k
        """
        # 延迟初始化, 避免 import 时副作用
        self.intent_recognizer = IntentRecognizer()
        self.retriever = create_reranked_retriever(KNOWLEDGE_BASE, k=k)
        self.conversation_manager = ConversationManager(max_history=10)

    def handle(
        self,
        user_input: str,
        session_id: str = "default",
        history: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        处理一轮用户输入
        """
        t0 = time.time()

        # 1. 意图识别
        intent_result = self.intent_recognizer.recognize(
            user_input,
            context=history or []
        )
        intent = intent_result.intent.value
        intent_conf = intent_result.confidence
        is_p0_intent = intent_result.is_p0
        needs_risk = intent_result.needs_risk_disclosure

        # 2. L0 红线检测
        l0 = check_l0(user_input)
        l0_triggered = l0["l0_triggered"]

        # 3. 分流: L0 触发 -> 标准话术 + 转人工 (不调 LLM)
        if l0_triggered:
            # 选最严重的子类作模板
            categories = l0["categories"]
            most_severe = categories[0]["sub_category"] if categories else "default"
            # 转人工类映射
            template_key = self._match_template_key(most_severe)
            answer = L0_RESPONSE_TEMPLATES.get(template_key, L0_RESPONSE_TEMPLATES["default"])
            action = "transfer_human"

            result = {
                "answer": answer,
                "intent": intent,
                "intent_confidence": intent_conf,
                "action": action,
                "l0_triggered": True,
                "l0_categories": [
                    {"category": c["category"], "sub_category": c["sub_category"],
                     "human_readable": c.get("human_readable", "")}
                    for c in categories
                ],
                "sources": [],
                "elapsed_ms": round((time.time() - t0) * 1000, 1),
                "compliance": "L0 转人工, AI 不答业务",
            }
        else:
            # 4. RAG 检索
            retrieval_results = self.retriever.retrieve(user_input, top_k=3)
            sources = [r["id"] for r in retrieval_results]
            knowledge_context = "\n\n".join([
                f"【参考知识 {i+1}】\nID: {r['id']} [{r.get('domain', 'N/A')}]\n问题: {r['question']}\n回答: {r['answer']}"
                for i, r in enumerate(retrieval_results)
            ]) if retrieval_results else "（无相关知识）"

            # 5. LLM 生成
            action = "answer"
            system_prompt = self._build_system_prompt(intent, needs_risk)
            user_prompt = self._build_user_prompt(user_input, knowledge_context, history)

            t_llm = time.time()
            try:
                answer = llm_chat(
                    [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    max_tokens=500,
                )
            except Exception as e:
                answer = f"抱歉，系统繁忙请稍后重试（{type(e).__name__}）"
                action = "error"
            t_llm = (time.time() - t_llm) * 1000

            result = {
                "answer": answer,
                "intent": intent,
                "intent_confidence": intent_conf,
                "action": action,
                "l0_triggered": False,
                "l0_categories": [],
                "sources": sources,
                "retrieval_count": len(retrieval_results),
                "retrieval_method": retrieval_results[0].get("retrieval_method", "N/A") if retrieval_results else "N/A",
                "llm_elapsed_ms": round(t_llm, 1),
                "elapsed_ms": round((time.time() - t0) * 1000, 1),
                "compliance": "风险提示已附" if needs_risk else "正常",
            }

        # 6. 记录到会话历史
        self.conversation_manager.add_message(session_id, "user", user_input)
        self.conversation_manager.add_message(
            session_id, "assistant", result["answer"],
            metadata={"intent": intent, "action": action}
        )

        return result

    def _build_system_prompt(self, intent: str, needs_risk: bool) -> str:
        """构建系统提示"""
        base = (
            "你是招商银行智能客服小招. 简洁专业地回答用户问题, 控制在 200 字内. "
            "基于参考知识回答, 避免编造. 不在回答里说自己是 AI 助手."
        )
        if needs_risk:
            base += (
                " 涉及投资/理财/贷款类问题, 必须附风险提示: "
                "理财非存款, 投资有风险, 过往业绩不代表未来表现, 请根据风险承受能力选择."
            )
        if "loan" in intent or "credit" in intent:
            base += " 涉及贷款/信用卡, 必须说年化利率, 实际利率以审批为准."
        return base

    def _build_user_prompt(
        self, user_input: str, knowledge_context: str, history: Optional[List[Dict]]
    ) -> str:
        """构建用户提示"""
        parts = []
        if history:
            history_text = "\n".join([
                f"{m.get('role', 'user')}: {m.get('content', '')[:80]}"
                for m in history[-4:]
            ])
            parts.append(f"对话历史:\n{history_text}\n")
        parts.append(f"参考知识:\n{knowledge_context}\n")
        parts.append(f"用户问题: {user_input}")
        return "\n".join(parts)

    def _match_template_key(self, sub_category: str) -> str:
        """L0 子类 -> 模板 key 映射"""
        mapping = {
            "fraud_high_risk": "fraud_high_risk",
            "fake_official_speech": "fraud_fake_official",
            "fake_identity": "fraud_fake_official",
            "transfer_to_stranger": "fraud_transfer",
            "investment_fraud": "fraud_investment",
            "refund_lottery_fraud": "fraud_fake_official",
            "extortion": "fraud_fake_official",
            "large_amount": "aml_large",
            "structured_split": "aml_structured",
            "cash_intensive": "aml_large",
            "cross_border_suspicious": "aml_large",
            "third_party_payment": "aml_large",
            "related_party_suspicious": "aml_large",
            "proxy_query": "unauthorized_proxy_query",
            "proxy_transaction": "unauthorized_proxy_transaction",
            "unauthorized_op": "unauthorized_proxy_query",
            "identity_spoofing": "unauthorized_proxy_query",
        }
        return mapping.get(sub_category, "default")


# ============================================================
# 工厂函数
# ============================================================
def create_e2e_pipeline(k: int = 3) -> E2EPipeline:
    """工厂函数"""
    return E2EPipeline(k=k)
