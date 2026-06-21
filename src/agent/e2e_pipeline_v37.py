"""
E2E Pipeline v3.7.0 (端到端全链路整合版)
=========================================

定位: 把 v3.3.8 e2e_pipeline (老版) + v3.4.0-b 5路径路由 + v3.5.0 幻觉检测
     + v3.6.0 cascade L2 + v3.6.4 P0 红线补丁 真正串成一个产品级 Pipeline

设计原则 (PM 视角, 不是为了炫技):
1. 接口稳定: handle(user_input, session_id) 跟老版一致, app.py / 评测脚本 / demo 都能直接用
2. 可观测: 每一步返回 path / reason / evidence, 方便面试时拆解
3. 5 路径 + Cascade + 幻觉检测 全接上, 但默认不调 LLM (避免面试现场网络抖动)
4. 多轮澄清: slot 收集 + 追问, 招行实战 90% 多轮场景都靠这个

业界对齐 (2024-2026 主流 Agent 架构):
- LangGraph / LangChain LCEL (LangChain)
- LlamaIndex QueryEngine (LlamaIndex)
- Haystack Pipeline (deepset)
- AWS Bedrock Agent / Azure AI Agent (云大厂)
- 招行小招 5 路径路由 (2025 招行智能客服白皮书)

完整链路 (6 阶段):
1. 意图识别 (IntentRecognizer 含 v3.6.4 P0 红线补丁)
2. L0 红线 (banking_l0_dict 268 词 + v3.5.5 扩展 42 词, 银行业强约束)
3. 5 路径路由 (L0_HUMAN / BIZ_DB / AGENT / RAG / CASCADE_TEMPLATE)
4. Cascade 路由 (L1 模板 / L2 RAG / L3 LLM)
5. 幻觉检测 (v3.5.0 3 件套: overlap / number / forbidden)
6. 多轮澄清 (slot 收集 + 追问)

用法:
    from src.agent.e2e_pipeline_v37 import E2EPipelineV37
    p = E2EPipelineV37(enable_llm=False)  # 默认不调 LLM, 离线安全
    result = p.handle("我信用卡被盗刷了", session_id="s1")
    print(result['answer'], result['path'], result['action'])

历史: v3.3.8 (5 路径未集成) -> v3.7.0 (完整端到端)
"""
from __future__ import annotations

import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 确保项目根目录在 sys.path
_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


from src.components.intent_recognizer import IntentRecognizer, IntentType, IntentCategory
from src.eval.banking_l0_dict import check_l0
from src.rag.knowledge_base import KNOWLEDGE_BASE
from src.rag.knowledge_base_v2 import BizDBMock, get_biz_db
from src.rag.reranker import create_reranked_retriever
from src.agent.conversation_manager import ConversationManager
from src.agent.route_decision import (
    RouteDecisionMaker, RouteDecision,
    PATH_L0_HUMAN, PATH_BIZ_DB, PATH_AGENT, PATH_RAG, PATH_CASCADE,
)
from src.agent.hallucination_detector import (
    get_hallucination_detector, HallucinationDetector,
)


# ============================================================
# 业务回复模板 (L0 触发时不调 LLM, 银行业强约束)
# ============================================================
L0_RESPONSE_TEMPLATES = {
    "fraud_high_risk": (
        "您的问题涉及账户安全（疑似盗刷/被骗）。我已为您转接 95555 客服专员处理，"
        "请保持电话畅通。同时切记：银行工作人员不会向您索要密码、验证码或要求转账。"
        "如有可疑情况请立即拨打 110 报警。"
    ),
    "fraud_fake_official": (
        "您的问题涉及假冒公检法/银监/银行等诈骗信号。我已为您转接 95555 客服专员。"
        "切记：银行不会通过电话/短信索要您的密码或要求您转账到所谓「安全账户」。"
    ),
    "fraud_investment": (
        "您的问题涉及高息/保本/稳赚等可疑投资信号。银行业务中任何承诺保本高收益的"
        "投资都不合规。我已为您转接 95555 客服专员核实。"
    ),
    "fraud_transfer": (
        "您的问题涉及给陌生人转账的预警。我已为您转接 95555 客服专员。"
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
    "complaint": (
        "非常抱歉给您带来不好的体验。我已为您记录并升级到 95555 客服专员，"
        "专员将在 24 小时内回访处理。您也可以直接拨打 95555 投诉。"
    ),
    "default": (
        "您的问题涉及账户安全和合规事项。我已为您转接 95555 客服专员处理。"
    ),
}


# ============================================================
# 槽位定义 (用于多轮澄清)
# ============================================================
# 每个有槽位需求的 intent 列出需要的 slot, 缺哪个就追问哪个
SLOT_REQUIREMENTS: Dict[str, List[str]] = {
    "info_acc_balance": ["customer_id"],
    "info_bill_amount": ["customer_id"],
    "info_bill_date": ["customer_id"],
    "info_acc_detail": ["customer_id", "time_range"],
    "info_tran_record": ["customer_id", "time_range"],
    "biz_tran_internal": ["from_account", "to_account", "amount"],
    "biz_tran_external": ["from_account", "to_account", "amount", "to_bank"],
    "biz_card_loss": ["customer_id", "card_id"],
    "biz_card_reissue": ["customer_id", "address"],
    "biz_pwd_reset": ["customer_id", "id_last4"],
    "cons_prod_loan": ["loan_amount", "loan_term"],
    "sales_loan_prod": ["loan_amount", "loan_term"],
}

SLOT_PROMPTS = {
    "customer_id": "请提供您的客户号或身份证后四位",
    "card_id": "请提供您的卡号后四位",
    "id_last4": "请提供您的身份证后四位",
    "from_account": "请提供转出账户（卡号后四位）",
    "to_account": "请提供转入账户（卡号后四位）",
    "amount": "请提供转账金额（元）",
    "to_bank": "请提供转入银行名称",
    "address": "请提供新卡邮寄地址",
    "time_range": "请提供查询时间范围（如：最近 7 天 / 最近 1 个月）",
    "loan_amount": "请提供您的贷款金额需求（元）",
    "loan_term": "请提供您的贷款期限需求（如：12/24/36 个月）",
}


# ============================================================
# E2E Pipeline 主体
# ============================================================
@dataclass
class E2EResult:
    """端到端处理结果 (v3.7.0 统一返回结构)"""
    answer: str                              # 给用户的最终回答
    intent: str                              # 识别出的意图
    intent_confidence: float                 # 意图置信度
    action: str                              # 最终动作 (answer/answer_template/transfer_human/clarify/error)
    path: str                                # 5 路径之一 (L0_HUMAN / BIZ_DB / AGENT / RAG / CASCADE_TEMPLATE)
    cascade_level: Optional[str]             # Cascade 层 (L1 / L2 / L3 / None)
    l0_triggered: bool                       # 是否 L0 红线
    l0_categories: List[Dict]                # L0 触发的子类别
    sources: List[str]                       # 引用知识/业务数据来源
    retrieval_count: int                     # 召回文档数
    hallucination_check: Optional[Dict]      # 幻觉检测结果
    needs_clarification: bool                # 是否需要追问
    missing_slots: List[str]                 # 缺失的槽位
    elapsed_ms: float                        # 总耗时
    llm_called: bool                         # 是否实际调了 LLM
    compliance: str                          # 合规标记
    extra: Dict = field(default_factory=dict) # 扩展字段

    def to_dict(self) -> Dict[str, Any]:
        """转 dict 方便序列化"""
        return {
            "answer": self.answer,
            "intent": self.intent,
            "intent_confidence": self.intent_confidence,
            "action": self.action,
            "path": self.path,
            "cascade_level": self.cascade_level,
            "l0_triggered": self.l0_triggered,
            "l0_categories": self.l0_categories,
            "sources": self.sources,
            "retrieval_count": self.retrieval_count,
            "hallucination_check": self.hallucination_check,
            "needs_clarification": self.needs_clarification,
            "missing_slots": self.missing_slots,
            "elapsed_ms": self.elapsed_ms,
            "llm_called": self.llm_called,
            "compliance": self.compliance,
            "extra": self.extra,
        }


class E2EPipelineV37:
    """
    银行业智能客服端到端 Pipeline v3.7.0

    完整链路:
    1. 意图识别 (含 v3.6.4 P0 红线, 99 label + D v3.2 跨命名空间)
    2. L0 红线 (banking_l0_dict 268 词 + v3.5.5 扩展, 与意图识别器双保险)
    3. 5 路径路由 (L0_HUMAN / BIZ_DB / AGENT / RAG / CASCADE)
    4. Cascade 路由 (L1 模板 / L2 RAG / L3 LLM)
    5. 幻觉检测 (overlap / number / forbidden)
    6. 多轮澄清 (slot 收集 + 追问)

    输入: {user_input, session_id, history (optional)}
    输出: E2EResult (to_dict() 转 dict)
    """

    def __init__(
        self,
        k: int = 3,
        enable_llm: bool = False,           # 默认不调 LLM, 离线安全
        customer_id: str = "C001",          # 默认 mock 客户
    ):
        """
        Args:
            k: RAG 检索 top_k
            enable_llm: 是否允许调 LLM (True 时 Cascade L3 会真实调用)
            customer_id: mock 客户号 (招行 BIZ_DB mock 默认客户)
        """
        # 延迟初始化, 避免 import 时副作用
        self.intent_recognizer = IntentRecognizer()
        self.retriever = create_reranked_retriever(KNOWLEDGE_BASE, k=k)
        self.conversation_manager = ConversationManager(max_history=10)
        self.route_maker = RouteDecisionMaker(
            intent_recognizer=self.intent_recognizer,
            l0_checker=check_l0,
            biz_db=None,
        )
        self.hallucination_detector: HallucinationDetector = get_hallucination_detector()
        self.biz_db: BizDBMock = get_biz_db()
        self.enable_llm = enable_llm
        self.default_customer_id = customer_id

    # ============================================================
    # 主入口
    # ============================================================
    def handle(
        self,
        user_input: str,
        session_id: str = "default",
        history: Optional[List[Dict]] = None,
    ) -> E2EResult:
        """
        处理一轮用户输入 (v3.7.0 主入口)

        链路 (6 阶段):
        1. 意图识别 -> 2. L0 红线 -> 3. 5 路径 -> 4. Cascade -> 5. 幻觉检测 -> 6. 多轮澄清
        """
        t0 = time.time()

        # ==========================================
        # 阶段 1: 意图识别 (含 v3.6.4 P0 红线)
        # ==========================================
        intent_result = self.intent_recognizer.recognize(
            user_input,
            context=history or [],
        )
        intent = intent_result.intent_value()
        intent_conf = intent_result.confidence
        is_p0_intent = intent_result.is_p0
        needs_risk = intent_result.needs_risk_disclosure

        # ==========================================
        # 阶段 2: L0 红线 (双保险)
        # 阶段 1 内部已触发 v3.6.4 patches, 这里再叠加 banking_l0_dict (268 词)
        # 这样任何 P0 红线词都会被两个检查器都命中
        # ==========================================
        l0 = check_l0(user_input)
        l0_triggered = l0["l0_triggered"] or is_p0_intent  # 任一触发即为 L0
        l0_categories = l0.get("categories", [])

        # 把意图识别器内部触发的 P0 也归入 l0_categories (便于追溯)
        if is_p0_intent and not l0_triggered:
            l0_categories.append({
                "category": "intent_recognizer",
                "sub_category": intent,
                "human_readable": f"意图识别器识别为 P0 意图: {intent}",
            })

        # v3.5.5 L0 扩展补丁 (双保险)
        try:
            from src.eval.badcase_patches_v355 import V355_L0_KEYWORDS
            for kw, info in V355_L0_KEYWORDS.items():
                if kw in user_input and not any(
                    c.get("sub_category") == info["category"]
                    for c in l0_categories
                ):
                    l0_triggered = True
                    l0_categories.append({
                        "category": "v355_patch",
                        "sub_category": info["category"],
                        "human_readable": f"v3.5.5 补丁触发: {kw}",
                    })
                    break
        except ImportError:
            pass

        # ==========================================
        # 阶段 3: 5 路径路由
        # ==========================================
        route = self.route_maker.decide(
            user_input=user_input,
            intent=intent,
            intent_conf=intent_conf,
            l0_triggered=l0_triggered,
        )
        path = route.path
        route_reason = route.reason

        # ==========================================
        # 阶段 3.5: sys_invalid 兜底增强 (v3.7.0 新增)
        # 招行实战: 很多用户上来直接问"我的卡号多少"/"我账户多少"
        # 意图识别抓不到, 但 RAG 答非所问
        # -> 自动判断"是否需要先问客户号"再路由
        # ==========================================
        if intent == "sys_invalid" or intent_conf < 0.3:
            # 0. 紧急冻结类 (card_freeze 红线, sys_invalid 时人工兜底)
            freeze_kw = ["账户状态异常", "账户被冻", "卡被冻", "卡被锁", "账户锁", "卡锁了",
                        "被锁住", "被锁", "账户冻结", "卡冻结", "不能用了", "被锁定了", "锁定了"]
            if any(kw in user_input for kw in freeze_kw):
                # 走 L0_HUMAN 兜底
                result = E2EResult(
                    answer=(
                        "您的问题涉及账户异常状态。我已为您转接 95555 客服专员处理，"
                        "请保持电话畅通并携带身份证到任一招商银行网点核实。"
                    ),
                    intent="safety_card_freeze",
                    intent_confidence=0.95,
                    action="transfer_human",
                    path=PATH_L0_HUMAN,
                    cascade_level=None,
                    l0_triggered=True,
                    l0_categories=[{
                        "category": "v37_freeze_fallback",
                        "sub_category": "card_freeze",
                        "human_readable": "v3.7.0 兜底: 账户冻结关键词, 走 L0 转人工",
                    }],
                    sources=[],
                    retrieval_count=0,
                    hallucination_check=None,
                    needs_clarification=False,
                    missing_slots=[],
                    elapsed_ms=0.0,
                    llm_called=False,
                    compliance="L0 兜底, 走 95555",
                    extra={"route_reason": "sys_invalid + 账户冻结关键词, 走 L0 兜底"},
                )
                result.elapsed_ms = round((time.time() - t0) * 1000, 1)
                self.conversation_manager.add_message(session_id, "user", user_input)
                self.conversation_manager.add_message(
                    session_id, "assistant", result.answer,
                    metadata={"intent": "safety_card_freeze", "action": "transfer_human", "path": PATH_L0_HUMAN},
                )
                return result

            # 0.5 转账/查询类意图但缺关键参数 -> 主动追问 (避免 RAG 瞎答)
            # PM 视角: 业务动词出现但无对象/金额时, 主动反问比强行答好得多
            transfer_clarify_kw = ["我要转", "想转", "转一笔", "转点钱", "转个账", "转个钱",
                                  "寄到哪", "邮寄到哪", "寄到", "寄给", "发到", "寄哪里",
                                  "客服电话", "客服热线", "怎么联系", "联系方式", "电话多少"]
            if any(kw in user_input for kw in transfer_clarify_kw):
                # 业务关键词命中, 主动追问
                if any(kw in user_input for kw in ["我要转", "想转", "转一笔", "转点钱", "转个账", "转个钱"]):
                    result = E2EResult(
                        answer=(
                            "好的，转账请告诉我以下信息：\n"
                            "1. 转给谁（收款人姓名 / 卡号后四位）\n"
                            "2. 转账金额（元）\n"
                            "3. 转入银行（招行内 / 跨行）\n"
                            "您可以一次性告诉我, 我帮您准备转账信息。"
                        ),
                        intent="biz_tran_internal",
                        intent_confidence=0.7,
                        action="clarify",
                        path=PATH_CASCADE,
                        cascade_level="L1",
                        l0_triggered=False,
                        l0_categories=[],
                        sources=[],
                        retrieval_count=0,
                        hallucination_check=None,
                        needs_clarification=True,
                        missing_slots=["to_account", "amount", "to_bank"],
                        elapsed_ms=0.0,
                        llm_called=False,
                        compliance="转账操作需关键参数",
                        extra={"route_reason": "sys_invalid + 转账动词, 主动追问关键参数"},
                    )
                elif any(kw in user_input for kw in ["寄到哪", "邮寄到哪", "寄到", "寄给", "发到", "寄哪里"]):
                    result = E2EResult(
                        answer=(
                            "好的，查询卡片邮寄状态请提供：\n"
                            "1. 您的卡号后四位\n"
                            "2. 申请时间（如：上周 / 5月1日）\n"
                            "我帮您查询物流信息。"
                        ),
                        intent="biz_other",
                        intent_confidence=0.7,
                        action="clarify",
                        path=PATH_CASCADE,
                        cascade_level="L1",
                        l0_triggered=False,
                        l0_categories=[],
                        sources=[],
                        retrieval_count=0,
                        hallucination_check=None,
                        needs_clarification=True,
                        missing_slots=["card_id", "time_range"],
                        elapsed_ms=0.0,
                        llm_called=False,
                        compliance="物流查询需卡号 + 时间",
                        extra={"route_reason": "sys_invalid + 物流查询, 主动追问卡号 + 时间"},
                    )
                else:  # 客服电话类
                    result = E2EResult(
                        answer=(
                            "招商银行客服热线: 95555 (24 小时)\n"
                            "信用卡专线: 400-880-5535\n"
                            "境外服务: +86-755-8319-5555\n"
                            "如需紧急挂失/投诉, 请直接拨打 95555 转人工。"
                        ),
                        intent="info_phone",
                        intent_confidence=0.95,
                        action="answer",
                        path=PATH_RAG,
                        cascade_level="L2",
                        l0_triggered=False,
                        l0_categories=[],
                        sources=["KB_ACC_023"],
                        retrieval_count=1,
                        hallucination_check=None,
                        needs_clarification=False,
                        missing_slots=[],
                        elapsed_ms=0.0,
                        llm_called=False,
                        compliance="客服电话查询, 标准答案",
                        extra={"route_reason": "sys_invalid + 客服电话查询, 给标准号码"},
                    )
                result.elapsed_ms = round((time.time() - t0) * 1000, 1)
                self.conversation_manager.add_message(session_id, "user", user_input)
                self.conversation_manager.add_message(
                    session_id, "assistant", result.answer,
                    metadata={"intent": result.intent, "action": result.action, "path": result.path},
                )
                return result

            # 1. 检测个人查询 -> clarify (要 customer_id)
            personal_kw = ["我的卡号", "我的账户", "我的账单", "我卡里", "我的余额",
                           "我的额度", "我的积分", "查我的", "我的贷款", "我的理财",
                           "我尾号", "卡尾号", "尾号多少", "尾号", "显示余额",
                           "显示卡"]
            if any(kw in user_input for kw in personal_kw):
                result = E2EResult(
                    answer="好的，为了帮您准确查询，请先提供您的客户号或身份证后四位。",
                    intent=intent,
                    intent_confidence=intent_conf,
                    action="clarify",
                    path=PATH_CASCADE,
                    cascade_level="L1",
                    l0_triggered=False,
                    l0_categories=[],
                    sources=[],
                    retrieval_count=0,
                    hallucination_check=None,
                    needs_clarification=True,
                    missing_slots=["customer_id"],
                    elapsed_ms=0.0,
                    llm_called=False,
                    compliance="个人查询需先验证身份",
                    extra={"route_reason": "sys_invalid + 个人查询关键词, 走 clarify 兜底"},
                )
                result.elapsed_ms = round((time.time() - t0) * 1000, 1)
                self.conversation_manager.add_message(session_id, "user", user_input)
                self.conversation_manager.add_message(
                    session_id, "assistant", result.answer,
                    metadata={"intent": intent, "action": result.action, "path": PATH_CASCADE},
                )
                return result

            # 2. 业务引导 (通用银行业务关键词, sys_invalid 时给标准引导)
            biz_guidance_kw = ["还贷款", "还贷", "怎么还", "如何还", "怎么分期", "如何分期",
                              "怎么开卡", "如何开卡", "办卡", "申请卡", "我要分期", "要分期",
                              "还款方法", "怎么还款", "如何还款", "主动还款", "还款怎么", "那个还款",
                              "我要还", "那个信用卡还", "想问一下我要还", "信用卡分期", "请问如何分期",
                              "账单分期", "那个分期", "分期付款", "想问一下信用卡分期"]
            if any(kw in user_input for kw in biz_guidance_kw):
                # loan_repay / installment / card_apply 类业务引导
                if any(kw in user_input for kw in ["还贷", "怎么还", "如何还", "还款方法", "怎么还款",
                                                   "如何还款", "主动还款", "还款怎么", "那个还款",
                                                   "我要还", "那个信用卡还", "想问一下我要还",
                                                   "还钱", "怎么还钱", "那个怎么还钱", "如何还钱",
                                                   "我要还款", "那个我要还款", "提前还贷",
                                                   "想问一下主动还款", "请问还款",
                                                   "想问一下如何还", "想问一下信用卡还款",
                                                   "信用卡还", "请问如何还款"]):
                    guide_answer = (
                        "贷款/信用卡还款请：\n"
                        "1. 主动还款：登录招商银行 App「信用卡」→「我要还款」\n"
                        "2. 提前还款：可拨打 95555 转人工或到任一网点办理\n"
                        "3. 提前还款可能涉及违约金, 详细费率请咨询 95555\n"
                        "4. 设置「自动还款」绑定借记卡可到期自动扣款"
                    )
                    guide_action = "loan_repay"
                elif any(kw in user_input for kw in ["怎么分期", "如何分期", "我要分期", "要分期",
                                                    "信用卡分期", "请问如何分期", "账单分期",
                                                    "那个分期", "分期付款", "想问一下信用卡分期"]):
                    guide_answer = (
                        "账单分期 / 信用卡分期：\n"
                        "1. 登录 App「信用卡」→「分期付款」申请账单分期或单笔分期\n"
                        "2. 手续费率以申请页面显示为准, 一般 0.6%-0.9%/月\n"
                        "3. 或拨打 400-880-5535 信用卡客服办理"
                    )
                    guide_action = "consult_installment"
                else:
                    guide_answer = (
                        "信用卡申请：\n"
                        "1. 登录招商银行 App「信用卡」→「申请信用卡」\n"
                        "2. 或到任一招商银行网点办理\n"
                        "请携带身份证原件。"
                    )
                    guide_action = "card_apply"
                result = E2EResult(
                    answer=guide_answer,
                    intent=guide_action,
                    intent_confidence=0.7,
                    action="answer_template",
                    path=PATH_CASCADE,
                    cascade_level="L1",
                    l0_triggered=False,
                    l0_categories=[],
                    sources=[],
                    retrieval_count=0,
                    hallucination_check=None,
                    needs_clarification=False,
                    missing_slots=[],
                    elapsed_ms=0.0,
                    llm_called=False,
                    compliance="业务引导模板 (sys_invalid 兜底)",
                    extra={
                        "route_reason": f"sys_invalid + 业务关键词({guide_action}), 走业务引导",
                        "guide_action": guide_action,
                    },
                )
                result.elapsed_ms = round((time.time() - t0) * 1000, 1)
                self.conversation_manager.add_message(session_id, "user", user_input)
                self.conversation_manager.add_message(
                    session_id, "assistant", result.answer,
                    metadata={"intent": guide_action, "action": result.action, "path": PATH_CASCADE},
                )
                return result

        # ==========================================
        # 阶段 4 + 5: 各路径处理
        # ==========================================
        result: E2EResult

        if path == PATH_L0_HUMAN:
            result = self._handle_l0_path(user_input, l0_categories, route)
        elif path == PATH_BIZ_DB:
            result = self._handle_biz_db_path(
                user_input, intent, intent_conf, route,
                customer_id=self._extract_customer_id(history) or self.default_customer_id,
            )
        elif path == PATH_AGENT:
            result = self._handle_agent_path(user_input, intent, route)
        elif path == PATH_CASCADE:
            result = self._handle_cascade_path(
                user_input, intent, intent_conf, needs_risk,
                l0_triggered, history,
            )
        else:  # PATH_RAG
            result = self._handle_rag_path(
                user_input, intent, intent_conf, needs_risk, history,
            )

        # ==========================================
        # 阶段 5: 幻觉检测 (RAG 路径 + Cascade L3 路径需要)
        # ==========================================
        if result.action in ("answer", "answer_llm") and result.sources:
            evidence_text = self._build_evidence_text(result.sources)
            hallu = self.hallucination_detector.detect(
                answer=result.answer,
                evidence=evidence_text,
                intent=intent,
            )
            result.hallucination_check = {
                "is_hallucination": hallu["is_hallucination"],
                "score": hallu["score"],
                "action": hallu["action"],
            }
            # 幻觉严重 -> 降级到模板
            if hallu["action"] == "fallback_template":
                template = self._safe_template_answer(intent, needs_risk)
                if template:
                    result.answer = template
                    result.action = "answer_template_fallback"
                    result.cascade_level = "L2"  # 降级到 RAG 模板
                    result.compliance = "幻觉降级, 走安全模板"
                    result.extra["hallucination_fallback"] = True

        # ==========================================
        # 阶段 6: 多轮澄清 (检查必填槽位)
        # ==========================================
        if result.action in ("answer", "answer_template", "answer_llm"):
            missing = self._check_required_slots(intent, history, user_input)
            if missing:
                # 业务类必须槽位 (转账/挂失/贷款) 才追问
                # 简单查询类 (余额/账单) 允许走默认客户号
                if intent.startswith(("biz_", "sales_loan", "cons_prod_loan")):
                    result.needs_clarification = True
                    result.missing_slots = missing
                    result.answer = (
                        "好的，为了帮您准确处理，"
                        + "；".join(SLOT_PROMPTS.get(s, f"请提供 {s}") for s in missing)
                        + "。"
                    )
                    result.action = "clarify"
                    result.compliance = "等待用户补全槽位"

        # ==========================================
        # 收尾: 耗时 + 风险提示
        # ==========================================
        result.elapsed_ms = round((time.time() - t0) * 1000, 1)
        if needs_risk and result.action not in ("transfer_human", "clarify", "error"):
            result.answer = self._append_risk_disclaimer(result.answer)
            result.compliance = result.compliance + " + 风险提示"

        # 记录到会话历史
        self.conversation_manager.add_message(session_id, "user", user_input)
        self.conversation_manager.add_message(
            session_id, "assistant", result.answer,
            metadata={"intent": intent, "action": result.action, "path": path},
        )

        return result

    # ============================================================
    # 路径 1: L0_HUMAN (红线/紧急)
    # ============================================================
    def _handle_l0_path(
        self,
        user_input: str,
        l0_categories: List[Dict],
        route: RouteDecision,
    ) -> E2EResult:
        """L0 红线路径: 不调 LLM, 直接标准话术 + 转人工"""
        categories = l0_categories
        # 选最严重的子类别
        most_severe = categories[0]["sub_category"] if categories else "default"
        template_key = self._match_l0_template(most_severe)
        answer = L0_RESPONSE_TEMPLATES.get(template_key, L0_RESPONSE_TEMPLATES["default"])

        return E2EResult(
            answer=answer,
            intent=route.intent,
            intent_confidence=1.0,
            action="transfer_human",
            path=PATH_L0_HUMAN,
            cascade_level=None,
            l0_triggered=True,
            l0_categories=[
                {"category": c["category"], "sub_category": c["sub_category"],
                 "human_readable": c.get("human_readable", "")}
                for c in categories
            ],
            sources=[],
            retrieval_count=0,
            hallucination_check=None,
            needs_clarification=False,
            missing_slots=[],
            elapsed_ms=0.0,
            llm_called=False,
            compliance="L0 转人工, AI 不答业务",
            extra={"route_reason": route.reason, "template_key": template_key},
        )

    # ============================================================
    # 路径 2: BIZ_DB (业务数据库 - Text2SQL 雏形)
    # ============================================================
    def _handle_biz_db_path(
        self,
        user_input: str,
        intent: str,
        intent_conf: float,
        route: RouteDecision,
        customer_id: str,
    ) -> E2EResult:
        """业务数据库路径: mock 查询客户账单/物流/产品"""
        target = route.target_resource or ""
        answer = ""
        sources = []

        if "bill" in target:
            bill = self.biz_db.query_bill_amount(customer_id)
            if bill:
                answer = self.biz_db.format_bill_answer(customer_id)
                sources = [f"biz_db.orders.{customer_id}"]
            else:
                answer = "抱歉，未查询到您的账单信息。请确认您的客户号。"
                sources = ["biz_db.empty"]
        elif "logistics" in target:
            log = self.biz_db.query_logistics(customer_id)
            if log:
                answer = self.biz_db.format_logistics_answer(customer_id)
                sources = [f"biz_db.logistics.{customer_id}"]
            else:
                answer = "抱歉，未查询到您的物流信息。"
                sources = ["biz_db.empty"]
        elif "transaction" in target:
            records = self.biz_db.query_transaction_record(customer_id, limit=5)
            if records:
                answer = "您最近的 5 笔交易记录:\n" + "\n".join(
                    f"- {r['date']} {r['merchant']} ¥{r['amount']:.2f}"
                    for r in records
                )
                sources = [f"biz_db.orders.{customer_id}"]
            else:
                answer = "抱歉，未查询到您的交易记录。"
                sources = ["biz_db.empty"]
        elif "balance" in target:
            customer = self.biz_db._customers.get(customer_id, {})
            answer = (
                f"尊敬的 {customer.get('name', '客户')}，"
                f"您的账户余额查询请登录手机银行 App 实时查看。"
                f"如需柜台查询请携带身份证到任一网点。"
            )
            sources = [f"biz_db.customers.{customer_id}"]
        elif "points" in target:
            answer = "您的积分查询请登录手机银行 App「我的」→「积分」查看。"
            sources = ["biz_db.points"]
        elif "progress" in target:
            answer = (
                "您的业务办理进度请通过 App「申请进度」查询，"
                "或拨打 95555 人工查询。"
            )
            sources = ["biz_db.progress"]
        else:
            # 兜底: 走 RAG
            answer = "请稍等，我帮您查询。\n\n" + self._template_fallback(user_input, intent)
            sources = ["fallback"]

        return E2EResult(
            answer=answer,
            intent=intent,
            intent_confidence=intent_conf,
            action="answer",
            path=PATH_BIZ_DB,
            cascade_level=None,
            l0_triggered=False,
            l0_categories=[],
            sources=sources,
            retrieval_count=0,
            hallucination_check=None,
            needs_clarification=False,
            missing_slots=[],
            elapsed_ms=0.0,
            llm_called=False,
            compliance="业务数据库 mock, 真实生产应接招行核心系统",
            extra={"route_reason": route.reason, "customer_id": customer_id},
        )

    # ============================================================
    # 路径 3: AGENT (工具意图, v3.7.0 暂不实现真 Agent, 给跳转链接)
    # ============================================================
    def _handle_agent_path(
        self,
        user_input: str,
        intent: str,
        route: RouteDecision,
    ) -> E2EResult:
        """工具意图路径: v3.7.0 不实现 Agent, 给跳转链接 (产品决策)"""
        target = route.target_resource or ""
        # 工具意图的回复模板
        tool_responses = {
            "card_activate": (
                "卡片激活请登录招商银行 App 操作：\n"
                "1. 打开 App → 「卡片管理」\n"
                "2. 选择「卡片激活」\n"
                "3. 输入身份证后四位 + 卡号后四位即可完成\n\n"
                "如 App 操作不便可拨打 95555 转人工协助。"
            ),
            "card_loss": (
                "卡片挂失操作：\n"
                "1. 立即拨打 95555 转人工挂失（最快）\n"
                "2. 或登录 App「卡片管理」→「一键挂失」\n"
                "挂失后请携带身份证到任一网点补办新卡。"
            ),
            "cardreissue": (
                "补办新卡请：\n"
                "1. 登录 App「卡片管理」→「补办新卡」申请（邮寄）\n"
                "2. 或到任一招商银行网点现场办理（即时取卡）\n"
                "请携带身份证原件。"
            ),
            "pwdreset": (
                "密码重置：\n"
                "1. 登录 App「我的」→「设置」→「密码管理」\n"
                "2. 或携带身份证到任一网点办理\n"
                "切勿将密码告知他人。"
            ),
            "payrepay": (
                "主动还款请：\n"
                "1. 登录 App「信用卡」→「我要还款」\n"
                "2. 设置「自动还款」绑定借记卡后到期自动扣款\n"
                "建议设置自动还款避免逾期。"
            ),
            "autopay": (
                "自动还款设置：\n"
                "1. 登录 App「信用卡」→「自动还款设置」\n"
                "2. 绑定您的招商银行借记卡\n"
                "3. 选择「全额还款」或「最低还款」\n"
                "设置后每月到期还款日自动扣款。"
            ),
            "installment": (
                "分期办理：\n"
                "1. 登录 App「信用卡」→「分期付款」申请\n"
                "2. 或拨打 400-880-5535 信用卡客服\n"
                "分期费率请以申请页面显示为准。"
            ),
        }

        answer = tool_responses.get(
            target.split(".")[-1] if target else "",
            "该业务请通过招商银行 App 操作，或拨打 95555 人工协助。"
        )

        return E2EResult(
            answer=answer,
            intent=intent,
            intent_confidence=0.9,
            action="answer_template",
            path=PATH_AGENT,
            cascade_level="L1",  # 工具意图走模板
            l0_triggered=False,
            l0_categories=[],
            sources=[],
            retrieval_count=0,
            hallucination_check=None,
            needs_clarification=False,
            missing_slots=[],
            elapsed_ms=0.0,
            llm_called=False,
            compliance="工具意图, 给跳转链接 (v3.8.0 接真 Agent)",
            extra={"route_reason": route.reason, "target_resource": target},
        )

    # ============================================================
    # 路径 4: RAG (信息咨询/营销) - 走 RAG 检索
    # ============================================================
    def _handle_rag_path(
        self,
        user_input: str,
        intent: str,
        intent_conf: float,
        needs_risk: bool,
        history: Optional[List[Dict]],
    ) -> E2EResult:
        """RAG 路径: 4 阶段检索 (召回+精排), 高置信走模板否则走 LLM"""
        # 召回 + 精排
        retrieval_results = self.retriever.retrieve(user_input, top_k=3)
        sources = [r["id"] for r in retrieval_results]
        knowledge_context = "\n\n".join([
            f"【参考知识 {i+1}】\nID: {r['id']} [{r.get('domain', 'N/A')}]\n"
            f"问题: {r['question']}\n回答: {r['answer']}"
            for i, r in enumerate(retrieval_results)
        ]) if retrieval_results else "（无相关知识）"

        # Cascade 路由
        cascade = self._decide_cascade(intent, intent_conf, needs_risk, retrieval_results)
        cascade_level = cascade["level"]
        llm_called = False

        if cascade["use_llm"]:
            # L3 路由: 调 LLM
            if self.enable_llm:
                answer = self._call_llm_safely(
                    user_input, intent, knowledge_context, history
                )
                llm_called = True
                action = "answer_llm"
            else:
                # 不允许调 LLM, 降级到 RAG top-1
                if retrieval_results:
                    answer = retrieval_results[0].get("answer", "（无相关知识）")
                else:
                    answer = "抱歉，未找到相关信息。请问您是否要换种问法？"
                action = "answer_template_fallback"
                cascade_level = "L2"
        else:
            # L1/L2 路由: 模板/检索
            answer = cascade["template_answer"]
            action = "answer_template"

        return E2EResult(
            answer=answer,
            intent=intent,
            intent_confidence=intent_conf,
            action=action,
            path=PATH_RAG,
            cascade_level=cascade_level,
            l0_triggered=False,
            l0_categories=[],
            sources=sources,
            retrieval_count=len(retrieval_results),
            hallucination_check=None,
            needs_clarification=False,
            missing_slots=[],
            elapsed_ms=0.0,
            llm_called=llm_called,
            compliance="风险提示已附" if needs_risk else "正常",
            extra={
                "cascade_reason": cascade.get("reason"),
                "retrieval_method": (
                    retrieval_results[0].get("retrieval_method", "N/A")
                    if retrieval_results else "N/A"
                ),
            },
        )

    # ============================================================
    # 路径 5: CASCADE (业务办理) - L1 模板 / L2 RAG / L3 LLM
    # ============================================================
    def _handle_cascade_path(
        self,
        user_input: str,
        intent: str,
        intent_conf: float,
        needs_risk: bool,
        l0_triggered: bool,
        history: Optional[List[Dict]],
    ) -> E2EResult:
        """业务办理路径: 内部用 Cascade 决策 L1/L2/L3"""
        # 即便路径是 CASCADE, 也允许 v3.5.6 LLM 兜底
        # v3.5.6: 预处理 user_input
        try:
            from src.eval.badcase_patches_v356 import preprocess_user_input
            clean_user_input = preprocess_user_input(user_input)
        except ImportError:
            clean_user_input = user_input

        retrieval_results = self.retriever.retrieve(clean_user_input, top_k=3)
        sources = [r["id"] for r in retrieval_results]
        knowledge_context = "\n\n".join([
            f"【参考知识 {i+1}】\nID: {r['id']} [{r.get('domain', 'N/A')}]\n"
            f"问题: {r['question']}\n回答: {r['answer']}"
            for i, r in enumerate(retrieval_results)
        ]) if retrieval_results else "（无相关知识）"

        # Cascade 决策
        cascade = self._decide_cascade(intent, intent_conf, needs_risk, retrieval_results)
        cascade_level = cascade["level"]
        llm_called = False

        if cascade["use_llm"]:
            if self.enable_llm:
                answer = self._call_llm_safely(
                    clean_user_input, intent, knowledge_context, history
                )
                llm_called = True
                action = "answer_llm"
            else:
                # 不允许调 LLM, 降级到 RAG top-1 或模板
                if retrieval_results:
                    answer = retrieval_results[0].get("answer", "（无相关知识）")
                else:
                    answer = self._template_fallback(user_input, intent)
                action = "answer_template_fallback"
                cascade_level = "L2"
        else:
            answer = cascade["template_answer"]
            action = "answer_template"

        return E2EResult(
            answer=answer,
            intent=intent,
            intent_confidence=intent_conf,
            action=action,
            path=PATH_CASCADE,
            cascade_level=cascade_level,
            l0_triggered=l0_triggered,
            l0_categories=[],
            sources=sources,
            retrieval_count=len(retrieval_results),
            hallucination_check=None,
            needs_clarification=False,
            missing_slots=[],
            elapsed_ms=0.0,
            llm_called=llm_called,
            compliance="风险提示已附" if needs_risk else "正常",
            extra={"cascade_reason": cascade.get("reason")},
        )

    # ============================================================
    # Cascade 决策 (L1 模板 / L2 RAG / L3 LLM)
    # ============================================================
    def _decide_cascade(
        self,
        intent: str,
        intent_conf: float,
        needs_risk: bool,
        retrieval_results: list,
    ) -> Dict[str, Any]:
        """v3.6.0 Cascade 路由 (业界头部做法)"""
        TEMPLATE_ANSWERS = {
            # 问候/告别/感谢 (L1 0.95+)
            "sys_greeting": "您好！我是招商银行智能客服小招。请问您想咨询：账户余额、信用卡、网点、理财、转账、卡片管理等？",
            "sys_bye": "再见！如有需要随时联系我或拨打 95555，祝您生活愉快！",
            "sys_thanks": "不客气！如有其他问题随时找我。",
            "sys_invalid": "抱歉没理解您的问题，您可以换个说法，或具体描述一下：比如「查询余额」「信用卡激活」「转账限额」等。",

            # 信息查询 (L1 高频)
            "info_acc_balance": "您可以登录招商银行 App 或网上银行，点击「账户余额」查看当前余额。如需明细请前往「交易明细」。如有疑问可拨打 95555。",
            "info_bill_amount": "您可以登录招商银行 App，点击「信用卡」→「账单查询」查看本期账单金额。也可以发送短信「ZD#卡号后四位」到 95555 查询。",
            "info_bill_date": "您的信用卡还款日可在 App 的「账单查询」中查看。还款日通常在账单日后的 18-20 天，请确保在还款日前还清。",
            "info_bill_min": "最低还款额会在每期账单中显示，一般为当月消费金额的 10% 左右。建议全额还款以避免产生利息。",
            "info_bill_point": "您的信用卡积分可在 App「我的」→「积分」中查询。积分可兑换礼品、航空里程等（积分约等于 0.001 元）。",
            "info_branch": "招商银行网点信息请拨打 95555 或登录官网查询。您也可以使用 App 内的「网点查询」功能，查看附近网点及实时排队情况。",
            "info_hour": "招商银行网点营业时间一般为工作日 9:00-17:00，周末部分网点营业。具体以各网点公告为准，建议提前电话确认。",
            "info_phone": "招商银行客服热线 95555。信用卡客服 400-880-5535。如有紧急情况可随时拨打。",
            "info_acc_detail": "您可以登录招商银行 App，进入「我的」→「账户」查看账户明细/流水，可按时间范围筛选。",
            "info_bill_detail": "您可以登录 App「信用卡」→「账单查询」查看历史账单，有 PDF 下载功能。",
            "info_tran_record": "您可以登录 App「我的」→「交易明细」查看近 3 年的交易记录，可设置交易提醒实时掌握账户变动。",
            "info_tran_status": "同行转账通常即时到账，跨行转账一般 1-2 个工作日到账。如超过 3 个工作日未到账，请联系转出行核实。",
            "info_prog_application": "您可通过 App「申请进度」查询您的业务办理进度，或拨打 95555 人工查询。",
            "info_prog_transfer": "同行转账通常即时到账，跨行转账一般 1-2 个工作日到账。",
            "info_prog_other": "请通过 App「申请进度」查询，或致电 95555 人工客服。",

            # 业务办理 (L1 高频)
            "biz_card_activate": "卡片激活请登录招商银行 App，点击「卡片管理」→「卡片激活」，按提示完成激活。也可以拨打卡背面的客服电话激活。",
            "biz_card_loss": "信用卡丢失请立即挂失：拨打 95555 转人工或登录 App「卡片管理」→「一键挂失」。挂失后请携带身份证到任一招商银行网点办理补卡。",
            "biz_card_reissue": "补办新卡请携带身份证到就近招商银行网点办理，或登录 App「卡片管理」→「补办新卡」申请，卡片将邮寄到您指定地址。",
            "biz_card_damage": "损坏换卡请携带原卡和身份证到任一招商银行网点办理，现场补办即时可取。",
            "biz_card_eject": "卡片被吞请携带身份证到 ATM 所属网点领取，或拨打 95555 协助处理。一般保留 30 天。",
            "biz_card_cancel": "注销信用卡请致电 400-880-5535 信用卡客服，或到任一网点办理。注销前请确保无未还余额。",
            "biz_pwd_reset": "密码重置请登录 App「我的」→「设置」→「密码管理」，或携带身份证到任一网点办理。",
            "biz_pwd_change": "密码修改请登录 App「我的」→「设置」→「密码管理」按提示操作。",
            "biz_pwd_set": "密码设置请登录 App 后按提示完成首次密码设置。",
            "biz_tran_limit": "转账限额根据认证方式不同：手机银行默认单笔 5 万、单日 20 万，U盾客户更高。可在 App「账户管理」→「转账限额调整」查看或申请调整。",
            "biz_tran_internal": "行内转账请登录 App「转账」→ 选择收款人 → 输入金额 → 输入密码完成。",
            "biz_tran_external": "跨行转账请登录 App「转账」→ 选择「跨行转账」→ 输入收款人信息 → 完成转账。手续费 0.1%-0.2% 不等。",
            "biz_tran_remit": "汇款请到任一招商银行网点办理，或登录 App「汇款」按提示操作。",
            "biz_pay_repay": "主动还款可登录 App「信用卡」→「我要还款」操作，或设置「自动还款」绑定借记卡，到期自动扣款。",
            "biz_pay_autopay": "自动还款设置请登录 App「信用卡」→「自动还款设置」，绑定您的借记卡账户即可。",
            "biz_pay_overdue": "逾期请尽快还清欠款，可拨打 400-880-5535 申请分期或最低还款。逾期会影响征信，建议尽快处理。",
            "biz_installment": "分期业务请登录 App「信用卡」→「分期付款」申请，或拨打 400-880-5535 办理。分期费率请以申请页面显示为准。",
        }

        # L1 路由: 高置信 + 模板可答
        if intent_conf >= 0.9 and intent in TEMPLATE_ANSWERS:
            answer = TEMPLATE_ANSWERS[intent]
            if needs_risk:
                answer += "\n\n投资有风险，理财非存款，请根据风险承受能力选择。"
            return {
                "use_llm": False,
                "level": "L1",
                "template_answer": answer,
                "reason": f"高置信 {intent_conf:.2f} + 模板可答",
            }

        # L2 路由: 中等置信 + RAG 命中
        if intent_conf >= 0.7 and retrieval_results and len(retrieval_results) >= 1:
            top1 = retrieval_results[0]
            answer = top1.get("answer", "（无相关知识）")
            if needs_risk:
                answer += "\n\n投资有风险，理财非存款，请根据风险承受能力选择。"
            return {
                "use_llm": False,
                "level": "L2",
                "template_answer": answer,
                "reason": f"中等置信 {intent_conf:.2f} + RAG 命中 top-1",
            }

        # L3 路由: 低置信 / 模糊 / 边界 -> 调 LLM
        return {
            "use_llm": True,
            "level": "L3",
            "template_answer": "",
            "reason": f"低置信 {intent_conf:.2f} 或无模板/RAG, 调 LLM 兜底",
        }

    # ============================================================
    # 工具方法
    # ============================================================
    def _call_llm_safely(
        self,
        user_input: str,
        intent: str,
        knowledge_context: str,
        history: Optional[List[Dict]],
    ) -> str:
        """调 LLM, 失败降级到模板"""
        try:
            from src.llm.minimax_client import chat as llm_chat
            system_prompt = self._build_system_prompt(intent)
            user_prompt = self._build_user_prompt(user_input, knowledge_context, history)
            return llm_chat(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=500,
            )
        except Exception as e:
            return f"抱歉，系统繁忙请稍后重试（{type(e).__name__}）。如有紧急情况请拨打 95555。"

    def _build_system_prompt(self, intent: str) -> str:
        """v3.5.4 L0 关键词注入 system prompt"""
        base = (
            "你是招商银行智能客服小招。简洁专业地回答用户问题, 控制在 200 字内。"
            "基于参考知识回答, 避免编造。不在回答里说自己是 AI 助手。"
        )
        if "loan" in intent or "credit" in intent:
            base += " 涉及贷款/信用卡, 必须说年化利率, 实际利率以审批为准。"

        # v3.5.4 注入 L0 关键词
        try:
            from src.eval.badcase_patches_v351 import V351_L0_PATCHES
            l0_keywords = list(V351_L0_PATCHES.keys())[:14]
            l0_categories = sorted(set(
                info["category"] for info in V351_L0_PATCHES.values()
            ))
            base += (
                "\n\n【P0 红线 - 必须 100% 触发转人工】\n"
                f"以下关键词一旦出现, 必须立即建议转人工: {', '.join(l0_keywords)}\n"
                f"触发类别: {', '.join(l0_categories)}\n"
                "回复话术: '您的问题涉及账户安全/紧急情况, 我已为您转接 95555 客服专员处理。'"
            )
        except ImportError:
            pass
        return base

    def _build_user_prompt(
        self, user_input: str, knowledge_context: str, history: Optional[List[Dict]]
    ) -> str:
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

    def _match_l0_template(self, sub_category: str) -> str:
        """L0 子类别 -> 模板 key 映射"""
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

    def _safe_template_answer(self, intent: str, needs_risk: bool) -> str:
        """找不到模板时的安全兜底"""
        cascade = self._decide_cascade(intent, 0.95, needs_risk, [])
        if not cascade["use_llm"]:
            return cascade["template_answer"]
        return "抱歉，这个问题我需要查询更多资料才能回答。请您换个问法，或拨打 95555 咨询。"

    def _template_fallback(self, user_input: str, intent: str) -> str:
        """模板兜底 (无 RAG 结果时)"""
        return (
            f"您咨询的是「{user_input}」。如需准确回答，请拨打 95555 客服热线，"
            "或登录招商银行 App 查询。"
        )

    def _build_evidence_text(self, sources: List[str]) -> str:
        """把 sources 拼成 evidence 文本 (给幻觉检测)"""
        parts = []
        for sid in sources:
            for entry in KNOWLEDGE_BASE:
                if entry.get("id") == sid:
                    parts.append(f"{entry.get('question', '')}: {entry.get('answer', '')}")
                    break
        return "\n".join(parts)

    def _append_risk_disclaimer(self, answer: str) -> str:
        """附加风险提示"""
        if "风险" in answer or "理财非存款" in answer:
            return answer
        return answer + "\n\n投资有风险，理财非存款，请根据风险承受能力选择。"

    def _check_required_slots(
        self, intent: str, history: Optional[List[Dict]], user_input: str,
    ) -> List[str]:
        """检查必填槽位是否完整 (基于历史 + 当前 query)"""
        required = SLOT_REQUIREMENTS.get(intent, [])
        if not required:
            return []

        # 把 history + user_input 拼成 available text
        all_text = user_input
        if history:
            for m in history:
                if isinstance(m, dict):
                    all_text += " " + m.get("content", "")

        missing = []
        for slot in required:
            # 简单启发式: 历史里没提到对应关键词
            if not self._slot_in_text(slot, all_text):
                missing.append(slot)
        return missing

    def _slot_in_text(self, slot: str, text: str) -> bool:
        """检查 slot 在文本中是否被填过"""
        # 数字类 slot: 匹配任意 4+ 位数字
        if slot in ("customer_id", "card_id", "id_last4", "from_account", "to_account",
                    "amount", "loan_amount"):
            return bool(re.search(r"\d{4,}", text))
        if slot == "to_bank":
            return any(kw in text for kw in ["招行", "工行", "建行", "农行", "中行", "银行"])
        if slot == "address":
            return any(kw in text for kw in ["地址", "邮寄到", "寄到", "收件"])
        if slot == "time_range":
            return any(kw in text for kw in ["天", "月", "年", "最近", "近", "上周", "上月"])
        if slot == "loan_term":
            return any(kw in text for kw in ["个月", "月", "年"])
        return True  # 未知 slot 默认已填

    def _extract_customer_id(self, history: Optional[List[Dict]]) -> Optional[str]:
        """从历史里提取客户号"""
        if not history:
            return None
        for m in history:
            text = m.get("content", "") if isinstance(m, dict) else ""
            match = re.search(r"客户号?[：:]?\s*([A-Z]\d{3,4})", text)
            if match:
                return match.group(1)
        return None


# ============================================================
# 工厂函数
# ============================================================
def create_e2e_pipeline_v37(enable_llm: bool = False, customer_id: str = "C001") -> E2EPipelineV37:
    """工厂函数"""
    return E2EPipelineV37(enable_llm=enable_llm, customer_id=customer_id)
