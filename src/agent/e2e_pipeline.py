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

        # 2. L0 红线检测 (v3.5.5: 双重检测, 词典扩到 42 词)
        # 2a. 原 banking_l0_dict (268 词)
        l0 = check_l0(user_input)
        l0_triggered = l0["l0_triggered"]
        l0_categories = l0.get("categories", [])
        # 2b. v3.5.1 补丁 (14 词) + v3.5.5 扩展 (28 词) = 42 词
        try:
            from src.eval.badcase_patches_v355 import V355_L0_KEYWORDS
            for kw, info in V355_L0_KEYWORDS.items():
                if kw in user_input:
                    l0_triggered = True
                    if not any(c.get("sub_category") == info["category"] for c in l0_categories):
                        l0_categories.append({
                            "category": "v355_patch",
                            "sub_category": info["category"],
                            "human_readable": f"v3.5.5 补丁触发: {kw}",
                        })
                    break
        except ImportError:
            # 回退到 v3.5.1 补丁
            try:
                from src.eval.badcase_patches_v351 import V351_L0_PATCHES
                for kw, info in V351_L0_PATCHES.items():
                    if kw in user_input:
                        l0_triggered = True
                        break
            except ImportError:
                pass

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
            # v3.5.6: LLM 兜底前预处理 (去除"你好"/"谢谢"等寒暄词)
            try:
                from src.eval.badcase_patches_v356 import preprocess_user_input
                clean_user_input = preprocess_user_input(user_input)
            except ImportError:
                clean_user_input = user_input

            retrieval_results = self.retriever.retrieve(clean_user_input, top_k=3)
            sources = [r["id"] for r in retrieval_results]
            knowledge_context = "\n\n".join([
                f"【参考知识 {i+1}】\nID: {r['id']} [{r.get('domain', 'N/A')}]\n问题: {r['question']}\n回答: {r['answer']}"
                for i, r in enumerate(retrieval_results)
            ]) if retrieval_results else "（无相关知识）"

            # 5. v3.4.0 Cascade 路由: 决定要不要调 LLM
            # 业界头部做法 (Anthropic / LangGraph / AWS Bedrock Agent):
            # - L1 高置信规则 (>=0.95) + 模板能答 -> 不调 LLM
            # - L2 中等置信 (>=0.7) + 模板能答 -> 不调 LLM
            # - L3 低置信 / 模糊 / 无模板 -> 调 LLM
            # 银行业模板库覆盖: info_*/biz_card_*/sys_* (约 50% 样本)
            cascade_decision = self._decide_cascade(
                intent, intent_conf, needs_risk, retrieval_results
            )

            if cascade_decision["use_llm"]:
                # LLM 路由
                action = "answer"
                system_prompt = self._build_system_prompt(intent, needs_risk)
                user_prompt = self._build_user_prompt(clean_user_input, knowledge_context, history)

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
            else:
                # 模板路由 (不调 LLM, 银行业模板 + 知识库)
                action = "answer_template"
                answer = cascade_decision["template_answer"]
                t_llm = 0
                retrieval_results = cascade_decision.get("template_sources", retrieval_results)

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
                "cascade": cascade_decision["level"],  # L1 / L2 / L3
                "llm_called": cascade_decision["use_llm"],
            }

        # 6. 记录到会话历史
        self.conversation_manager.add_message(session_id, "user", user_input)
        self.conversation_manager.add_message(
            session_id, "assistant", result["answer"],
            metadata={"intent": intent, "action": action}
        )

        return result

    def _build_system_prompt(self, intent: str, needs_risk: bool) -> str:
        """构建系统提示 (v3.5.4 注入 L0 关键词 + 必含话术)"""
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

        # v3.5.4: 注入 L0 关键词 + 转人工规则 (P0 红线)
        # 原因: v3.5.3 发现 LLM cascade L3 兜底没看到 v3.5.1 L0 规则补丁, P0 Recall 50%
        # 修复: 把 L0 关键词直接注入 system_prompt, 让 LLM 也认这些词触发转人工
        try:
            from src.eval.badcase_patches_v351 import V351_L0_PATCHES
            l0_keywords = list(V351_L0_PATCHES.keys())[:14]  # 14 个 P0 关键词
            l0_categories = sorted(set(
                info["category"] for info in V351_L0_PATCHES.values()
            ))
            base += (
                "\n\n【P0 红线 - 必须 100% 触发转人工】"
                f"\n以下关键词一旦出现, 必须立即建议转人工 (不要尝试自己回答): "
                f"{', '.join(l0_keywords)}"
                f"\n触发类别: {', '.join(l0_categories)}"
                "\n回复话术: '您的问题涉及账户安全/紧急情况, 我已为您转接 95555 客服专员处理.'"
            )
        except ImportError:
            pass
        return base

    def _decide_cascade(
        self,
        intent: str,
        intent_conf: float,
        needs_risk: bool,
        retrieval_results: list,
    ) -> Dict[str, Any]:
        """
        v3.4.0 Cascade 路由: 决定要不要调 LLM

        业界头部做法 (Anthropic Haiku/Opus, LangGraph conditional, AWS Bedrock Agent):
        - L1 (规则/模板): 高置信 + 模板能答 -> 不调 LLM
        - L2 (轻量分类器/检索): 中等置信 + 检索命中 -> 不调 LLM
        - L3 (LLM 兜底): 低置信 / 模糊 / 边界 -> 调 LLM

        Returns:
            {
                "use_llm": bool,
                "level": "L1" | "L2" | "L3",
                "template_answer": str (仅 L1/L2 模板路由有),
                "template_sources": list (模板路由的引用),
                "reason": str,
            }
        """
        # 模板库: 银行业高频业务, 模板可答
        TEMPLATE_ANSWERS = {
            # 问候/告别/感谢 — L1 0.95+ 规则
            "sys_greeting": "您好！我是招商银行智能客服小招，有什么可以帮您？您可以咨询：账户余额、信用卡、网点查询、理财产品、转账操作、卡片管理等。",
            "sys_bye": "再见！如有需要随时联系我们 95555，祝您生活愉快！",
            "sys_thanks": "不客气！如有其他问题随时找我。",
            "sys_invalid": "抱歉没理解您的问题，您可以换个说法，或具体描述一下：比如「查询余额」「信用卡激活」「转账限额」等。",

            # 信息查询 — L1 高频
            "info_acc_balance": "您可以登录招商银行 App 或网上银行，点击「账户余额」查看当前余额。如需明细请前往「交易明细」。如有疑问可拨打 95555。",
            "info_bill_amount": "您可以登录招商银行 App，点击「信用卡」→「账单查询」查看本期账单金额。也可以发送短信「ZD#卡号后四位」到 95555 查询。",
            "info_bill_date": "您的信用卡还款日可在 App 的「账单查询」中查看。还款日通常在账单日后的 18-20 天，请确保在还款日前还清。",
            "info_bill_min": "最低还款额会在每期账单中显示，一般为当月消费金额的 10% 左右。建议全额还款以避免产生利息。",
            "info_bill_point": "您的信用卡积分可在 App「我的」→「积分」中查询。积分可兑换礼品、航空里程等，1 积分约等于 0.001 元。",
            "info_branch": "招商银行网点信息请拨打 95555 或登录官网查询。您也可以使用 App 内的「网点查询」功能，查看附近网点及实时排队情况。",
            "info_hour": "招商银行网点营业时间一般为工作日 9:00-17:00，周末部分网点营业。具体以各网点公告为准，建议提前电话确认。",
            "info_phone": "招商银行客服热线：95555。信用卡客服：400-880-5535。如有紧急情况可随时拨打。",
            "info_acc_detail": "您可以登录招商银行 App，进入「我的」→「账户」查看账户明细/流水，可按时间范围筛选。",
            "info_bill_detail": "您可以登录 App「信用卡」→「账单查询」查看历史账单，含 PDF 下载功能。",
            "info_tran_record": "您可以登录 App「我的」→「交易明细」查看近 3 年的交易记录，可设置交易提醒实时掌握账户变动。",
            "info_tran_status": "同行转账通常即时到账，跨行转账一般 1-2 个工作日到账。如超过 3 个工作日未到账，请联系转出行核实。",
            "info_prog_application": "您可通过 App「申请进度」查询您的业务办理进度，或拨打 95555 人工查询。",
            "info_prog_transfer": "同行转账通常即时到账，跨行转账一般 1-2 个工作日到账。",
            "info_prog_other": "请通过 App「申请进度」查询，或致电 95555 人工客服。",

            # 业务办理 — L1 高频
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

        # 1. L1 路由: 高置信规则 + 模板可答
        if intent_conf >= 0.9 and intent in TEMPLATE_ANSWERS:
            answer = TEMPLATE_ANSWERS[intent]
            # 加风险提示
            if needs_risk:
                answer += "\n\n投资有风险，理财非存款，请根据风险承受能力选择。"
            return {
                "use_llm": False,
                "level": "L1",
                "template_answer": answer,
                "template_sources": [],
                "reason": f"高置信 {intent_conf:.2f} + 模板可答",
            }

        # 2. L2 路由: 中等置信 + RAG 检索命中
        if intent_conf >= 0.7 and retrieval_results and len(retrieval_results) >= 2:
            # 用 RAG top-1 直接答 (知识库条目里已有完整答案)
            top1 = retrieval_results[0]
            answer = top1.get("answer", "（无相关知识）")
            if needs_risk:
                answer += "\n\n投资有风险，理财非存款，请根据风险承受能力选择。"
            return {
                "use_llm": False,
                "level": "L2",
                "template_answer": answer,
                "template_sources": retrieval_results[:1],
                "reason": f"中等置信 {intent_conf:.2f} + RAG 命中",
            }

        # 3. L3 路由: 低置信 / 模糊 / 边界 -> 调 LLM
        return {
            "use_llm": True,
            "level": "L3",
            "template_answer": "",
            "template_sources": [],
            "reason": f"低置信 {intent_conf:.2f} 或无模板, 调 LLM 兜底",
        }

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
