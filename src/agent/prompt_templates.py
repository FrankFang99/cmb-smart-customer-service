"""
v3.4.0-b 多套 Prompt 模板管理
==============================

业界对齐: 招行 / 微众 / 蚂蚁 都在 2025-2026 把"一个大 Prompt"拆为
"按业务类型定制的多套 Prompt 模板" (10-30 套)

设计:
- 12 套业务模板 (贷款/反诈/反洗钱/挂失/余额/投资/隐私/投诉/限额/通用/转人工/道歉)
- 每套模板独立: system_prompt + 后处理规则 + 风险话术
- 模板可扩展 (新业务直接加)
- 0 依赖 (纯 dict)
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional


# ============================================================
# 12 套业务模板
# ============================================================
PROMPT_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "loan_consult": {
        "name": "贷款咨询",
        "intent_prefixes": ["consult_ln", "sales_loan_prod", "info_loan_"],
        "system_prompt": (
            "你是招商银行智能客服小招, 负责解答贷款相关问题。\n"
            "【强制要求】\n"
            "1. 涉及年化利率/单利/复利, 必须明确标注, 不能只说'利率低'\n"
            "2. 必须说'具体利率以审批结果为准'\n"
            "3. 涉及额度/期数, 标明范围, 不承诺具体值\n"
            "4. 涉及风险, 加'贷款有风险, 请根据自身情况理性借贷'\n"
            "5. 严禁承诺'百分百下款' / '百分百通过'\n"
        ),
        "post_process": ["inject_risk_disclosure_loan", "check_no_guarantee_phrase"],
        "risk_phrases": ["贷款有风险", "理性借贷", "以审批结果为准"],
    },
    "fraud_warning": {
        "name": "反诈骗",
        "intent_prefixes": ["sec_fraud", "cons_urg_loss", "cons_comp_fraud"],
        "system_prompt": (
            "你是招商银行智能客服小招, 负责反诈骗相关问题。\n"
            "【强制要求】\n"
            "1. 涉及'被骗/盗刷/假冒', 必须强转人工, 不能用模板答\n"
            "2. 必须说'请注意防范电信诈骗, 我行不会通过电话/短信索要您的密码/验证码'\n"
            "3. 必须说'请立即拨打 95555 转人工挂失'\n"
            "4. 涉及报案, 引导拨打 110\n"
        ),
        "post_process": ["force_transfer_human", "inject_fraud_warning"],
        "risk_phrases": ["请注意防范电信诈骗", "我行不会索要", "立即拨打 95555"],
    },
    "aml_check": {
        "name": "反洗钱",
        "intent_prefixes": ["risk_aml", "risk_structured", "risk_cash"],
        "system_prompt": (
            "你是招商银行智能客服小招, 涉及反洗钱合规。\n"
            "【强制要求】\n"
            "1. 涉及'分多笔/拆单/兑换外币/给陌生人转', 强转人工 + 合规上报\n"
            "2. 必须说'根据反洗钱法律法规, 我行需对大额和可疑交易进行监控和报告'\n"
            "3. 严禁引导规避监管\n"
        ),
        "post_process": ["force_transfer_human", "inject_aml_compliance", "compliance_report"],
        "risk_phrases": ["反洗钱法律法规", "监控和报告"],
    },
    "card_loss": {
        "name": "挂失",
        "intent_prefixes": ["biz_card_loss", "cons_urg_card"],
        "system_prompt": (
            "你是招商银行智能客服小招, 涉及卡片挂失。\n"
            "【强制要求】\n"
            "1. 卡片丢失/被盗, 强转人工, 引导拨打 95555\n"
            "2. 必须说'请立即挂失 + 携带身份证到网点补卡'\n"
            "3. 涉及盗刷, 加'请保留证据 + 报警 110'\n"
        ),
        "post_process": ["force_transfer_human", "inject_card_loss_steps"],
        "risk_phrases": ["立即挂失", "95555", "报警 110"],
    },
    "balance_query": {
        "name": "余额查询",
        "intent_prefixes": ["info_bill_amount", "info_acc_balance", "info_acc_detail"],
        "system_prompt": (
            "你是招商银行智能客服小招, 解答账户/账单查询问题。\n"
            "【强制要求】\n"
            "1. 必须引导到 App/网银/95555 自助查询, 不能编造金额\n"
            "2. 涉及具体金额, 强转业务数据库 (Text2SQL/API)\n"
            "3. 不确定时, 严禁猜测, 必须说'请登录 App 查看或拨打 95555'\n"
        ),
        "post_process": ["no_guess_amount", "guide_to_app"],
        "risk_phrases": ["请登录 App", "95555"],
    },
    "investment_risk": {
        "name": "投资理财",
        "intent_prefixes": ["sales_wealth", "marketing_inv", "consult_inv"],
        "system_prompt": (
            "你是招商银行智能客服小招, 解答投资理财问题。\n"
            "【强制要求】\n"
            "1. 涉及预期收益, 必须说'非存款, 不保本, 不保息'\n"
            "2. 涉及风险等级, 必须说 R1/R2/R3 等具体等级\n"
            "3. 必须加'投资有风险, 理财非存款, 请根据风险承受能力选择'\n"
            "4. 严禁承诺'保本/高收益/无风险'\n"
        ),
        "post_process": ["inject_risk_disclosure_investment", "check_no_guarantee_phrase"],
        "risk_phrases": ["投资有风险", "理财非存款", "不保本", "风险承受能力"],
    },
    "privacy": {
        "name": "个人信息保护",
        "intent_prefixes": ["sec_privacy", "info_privacy", "cons_comp_privacy"],
        "system_prompt": (
            "你是招商银行智能客服小招, 涉及个人信息保护。\n"
            "【强制要求】\n"
            "1. 必须说'我行严格遵守《中华人民共和国个人信息保护法》'\n"
            "2. 不收集与业务无关的个人信息\n"
            "3. 客户有查询/更正/删除个人信息的权利\n"
        ),
        "post_process": ["inject_privacy_compliance"],
        "risk_phrases": ["《个人信息保护法》", "查询/更正/删除"],
    },
    "complaint": {
        "name": "投诉",
        "intent_prefixes": ["cons_comp_", "cons_urg_complaint"],
        "system_prompt": (
            "你是招商银行智能客服小招, 处理客户投诉。\n"
            "【强制要求】\n"
            "1. 先共情: '非常理解您的心情, 我会立即为您处理'\n"
            "2. 致歉: '对此给您带来的不便, 我们深表歉意'\n"
            "3. 解决方案 + 升级路径: '如需进一步协助, 我可为您转接资深客服'\n"
            "4. 留联系方式: '如需回访, 请提供您的联系方式'\n"
        ),
        "post_process": ["inject_complaint_template", "optional_transfer_human"],
        "risk_phrases": ["非常理解", "深表歉意", "立即为您处理"],
    },
    "transfer_limit": {
        "name": "转账限额",
        "intent_prefixes": ["info_tran_", "biz_tran_", "cons_tran_limit"],
        "system_prompt": (
            "你是招商银行智能客服小招, 解答转账限额问题。\n"
            "【强制要求】\n"
            "1. 必须区分'单笔/单日/单月'三种限额\n"
            "2. 必须说明认证方式对应限额 (手机银行/U盾/动态令牌)\n"
            "3. 涉及调整限额, 引导到 App '账户管理' 或网点办理\n"
        ),
        "post_process": ["check_no_specific_amount_guess"],
        "risk_phrases": ["单笔", "单日", "单月", "认证方式"],
    },
    "human_transfer": {
        "name": "转人工",
        "intent_prefixes": ["cons_urg_human"],
        "system_prompt": (
            "你是招商银行智能客服小招, 客户要求转人工。\n"
            "【强制要求】\n"
            "1. 立即转人工, 不挽留\n"
            "2. 必须说'正在为您转接人工客服, 请稍候'\n"
            "3. 严禁编造等待时长\n"
        ),
        "post_process": ["force_transfer_human"],
        "risk_phrases": ["正在为您转接人工客服", "请稍候"],
    },
    "apology": {
        "name": "道歉/服务异常",
        "intent_prefixes": ["sys_apology", "sys_invalid", "cons_comp_service"],
        "system_prompt": (
            "你是招商银行智能客服小招, 处理服务异常/道歉场景。\n"
            "【强制要求】\n"
            "1. 先致歉: '非常抱歉给您带来不便'\n"
            "2. 给出解决方案: '请重新尝试 / 拨打 95555 / 反馈具体问题'\n"
            "3. 不推诿, 不甩锅\n"
        ),
        "post_process": ["inject_apology_template"],
        "risk_phrases": ["非常抱歉", "不便"],
    },
    "general": {
        "name": "通用兜底",
        "intent_prefixes": ["*"],  # 兜底
        "system_prompt": (
            "你是招商银行智能客服小招。\n"
            "你可以咨询: 账户余额、信用卡、网点查询、理财产品、转账操作、卡片管理等。\n"
            "如不清楚, 请说'我帮您转接资深客服', 严禁编造信息。\n"
        ),
        "post_process": [],
        "risk_phrases": ["招商银行智能客服小招"],
    },
}


# ============================================================
# 模板管理器
# ============================================================
class PromptTemplateManager:
    """多套 Prompt 模板管理器"""

    def __init__(self, templates: Optional[Dict[str, Dict]] = None):
        self.templates = templates if templates is not None else PROMPT_TEMPLATES
        self._index: Dict[str, str] = {}  # intent_prefix -> template_id
        self._build_index()

    def _build_index(self):
        """构建意图前缀 -> 模板 ID 的索引"""
        self._index = {}
        for tid, tpl in self.templates.items():
            for prefix in tpl.get("intent_prefixes", []):
                if prefix == "*":
                    continue
                self._index[prefix] = tid

    def get_template(self, intent: str) -> Dict[str, Any]:
        """
        根据意图获取模板 (找不到返 general)
        """
        # 精确前缀匹配
        for prefix, tid in self._index.items():
            if intent.startswith(prefix):
                return self.templates[tid]
        # 兜底
        return self.templates["general"]

    def list_templates(self) -> List[Dict[str, Any]]:
        """列出所有模板"""
        return [
            {"id": tid, "name": tpl["name"], "intent_prefixes": tpl.get("intent_prefixes", [])}
            for tid, tpl in self.templates.items()
        ]

    def build_system_prompt(
        self,
        intent: str,
        user_query: str = "",
        knowledge_context: str = "",
    ) -> str:
        """
        构建完整的 system prompt (含基础 + 业务模板 + 知识库上下文)
        """
        tpl = self.get_template(intent)
        parts = [tpl["system_prompt"]]
        if knowledge_context:
            parts.append(
                f"\n【相关知识】\n{knowledge_context}\n请基于上述知识回答, 不要编造信息。"
            )
        if tpl.get("risk_phrases"):
            parts.append(
                "\n【必含话术】: " + " / ".join(tpl["risk_phrases"])
            )
        return "\n".join(parts)

    def post_process(self, intent: str, answer: str) -> str:
        """
        后处理 (按模板的 post_process 规则)
        当前是空操作 (预留接口, 真正接 LLM 时可加敏感词过滤等)
        """
        tpl = self.get_template(intent)
        for rule in tpl.get("post_process", []):
            # 0 依赖原则: 当前为空操作, v3.5.0 接 LLM 后实现
            pass
        return answer

    def stats(self) -> Dict[str, Any]:
        """模板统计"""
        return {
            "total_templates": len(self.templates),
            "by_intent_coverage": {
                tid: len(tpl.get("intent_prefixes", []))
                for tid, tpl in self.templates.items()
            },
        }


# ============================================================
# 工厂
# ============================================================
def get_template_manager() -> PromptTemplateManager:
    """获取模板管理器"""
    return PromptTemplateManager()
