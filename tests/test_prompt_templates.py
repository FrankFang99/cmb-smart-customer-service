"""
测试 9: v3.4.0-b 多套 Prompt 模板管理
======================================
覆盖:
- 12 套业务模板
- 意图前缀匹配
- 兜底模板
- build_system_prompt
- 后处理
"""
import pytest

from src.agent.prompt_templates import (
    PROMPT_TEMPLATES,
    PromptTemplateManager,
    get_template_manager,
)


class TestPromptTemplates:
    """12 套业务模板测试"""

    @pytest.fixture
    def m(self):
        return get_template_manager()

    def test_total_templates(self, m):
        """12 套模板"""
        assert len(m.templates) == 12

    def test_required_templates_exist(self, m):
        """关键业务模板都存在"""
        required = [
            "loan_consult", "fraud_warning", "aml_check", "card_loss",
            "balance_query", "investment_risk", "privacy", "complaint",
            "transfer_limit", "human_transfer", "apology", "general",
        ]
        for tid in required:
            assert tid in m.templates
            tpl = m.templates[tid]
            assert "name" in tpl
            assert "system_prompt" in tpl
            assert "intent_prefixes" in tpl
            assert len(tpl["system_prompt"]) > 10  # prompt 不能太短

    def test_general_template_catch_all(self, m):
        """通用模板兜底"""
        tpl = m.templates["general"]
        assert "*" in tpl["intent_prefixes"]


class TestTemplateLookup:
    """模板查询测试"""

    @pytest.fixture
    def m(self):
        return get_template_manager()

    def test_loan_intent(self, m):
        """贷款类意图 -> loan_consult"""
        for intent in ["consult_ln_001", "sales_loan_prod", "info_loan_rate"]:
            tpl = m.get_template(intent)
            assert tpl["name"] == "贷款咨询"

    def test_fraud_intent(self, m):
        """反诈类意图 -> fraud_warning"""
        for intent in ["sec_fraud_report", "cons_urg_loss", "cons_comp_fraud"]:
            tpl = m.get_template(intent)
            assert tpl["name"] == "反诈骗"

    def test_aml_intent(self, m):
        """反洗钱类意图 -> aml_check"""
        for intent in ["risk_aml_001", "risk_structured_split"]:
            tpl = m.get_template(intent)
            assert tpl["name"] == "反洗钱"

    def test_investment_intent(self, m):
        """投资类意图 -> investment_risk"""
        for intent in ["sales_wealth_prod", "marketing_inv", "consult_inv"]:
            tpl = m.get_template(intent)
            assert tpl["name"] == "投资理财"
            # 投资类必须含"非存款"
            assert "非存款" in tpl["system_prompt"]

    def test_human_transfer_intent(self, m):
        """转人工类意图 -> human_transfer"""
        tpl = m.get_template("cons_urg_human")
        assert tpl["name"] == "转人工"
        # 必须含"正在为您转接"
        assert "正在为您转接" in tpl["system_prompt"]

    def test_unknown_intent_falls_back_to_general(self, m):
        """未知意图兜底"""
        tpl = m.get_template("unknown_xyz_999")
        assert tpl["name"] == "通用兜底"


class TestBuildSystemPrompt:
    """build_system_prompt 测试"""

    @pytest.fixture
    def m(self):
        return get_template_manager()

    def test_basic_prompt(self, m):
        """基础 prompt"""
        prompt = m.build_system_prompt("consult_ln_001")
        assert "招商银行智能客服小招" in prompt
        assert "年化利率" in prompt  # 贷款类必含
        assert "贷款有风险" in prompt  # 风险话术

    def test_prompt_with_knowledge(self, m):
        """含知识库的 prompt"""
        kb = "信用卡账单金额 12345.67 元"
        prompt = m.build_system_prompt("info_bill_amount", knowledge_context=kb)
        assert "相关知识" in prompt
        assert kb in prompt

    def test_prompt_with_risk_phrases(self, m):
        """投资类必含风险话术"""
        prompt = m.build_system_prompt("sales_wealth_prod")
        assert "必含话术" in prompt
        assert "投资有风险" in prompt
        assert "理财非存款" in prompt

    def test_prompt_fraud_warning_required(self, m):
        """反诈类必含强转人工话术"""
        prompt = m.build_system_prompt("sec_fraud_report")
        assert "95555" in prompt
        assert "请注意防范电信诈骗" in prompt


class TestPostProcess:
    """后处理测试"""

    @pytest.fixture
    def m(self):
        return get_template_manager()

    def test_post_process_runs(self, m):
        """后处理不报错 (当前为空操作)"""
        result = m.post_process("consult_ln_001", "test answer")
        assert result == "test answer"


class TestTemplateStats:
    """模板统计测试"""

    def test_stats(self):
        s = get_template_manager().stats()
        assert "total_templates" in s
        assert s["total_templates"] == 12
        assert "by_intent_coverage" in s
