"""
测试 2: 银行业 Adapter (合规 + 监管 + 转人工)
"""
import pytest
from src.eval.banking_adapter import BankingComplianceMixin


class TestBankingAdapter:
    """银行业合规 Adapter 测试"""

    def setup_method(self):
        """每个测试方法前创建一个 mixin 实例"""
        self.adapter = BankingComplianceMixin()

    def test_loan_scenario_requires_interest_disclosure(self):
        """贷款场景必须说年化利率 + 实际利率 + IRR"""
        result = self.adapter.check_regulatory_compliance(
            "我行信用贷贷款年化利率 3.5%-18%, 实际利率以审批为准, IRR 详见贷款合同, 费用透明",
            intent="loan_consult"
        )
        assert result["regulatory_compliant"] is True
        assert len(result["missing_phrases"]) == 0

    def test_loan_scenario_missing_interest_phrase(self):
        """贷款场景未说年化 → 不合规"""
        result = self.adapter.check_regulatory_compliance(
            "我行有信用贷产品, 欢迎申请",
            intent="loan_consult"
        )
        assert result["regulatory_compliant"] is False
        assert len(result["missing_phrases"]) > 0

    def test_fraud_scenario_requires_warning(self):
        """反诈骗场景必须提示防范 (含两个标准话术)"""
        result = self.adapter.check_regulatory_compliance(
            "请注意防范电信诈骗, 我行不会通过电话/短信索要您的密码",
            intent="fraud_report"
        )
        assert result["regulatory_compliant"] is True

    def test_fraud_keyword_transfer_human(self):
        """反诈骗关键词触发 → 必须转人工"""
        result = self.adapter.check_fraud_keywords("我信用卡被盗刷了")
        assert result["fraud_risk_detected"] is True

    def test_aml_keyword_compliance_report(self):
        """反洗钱关键词触发 → 必须上报合规"""
        result = self.adapter.check_aml_keywords("我想分多笔转, 每次不到 5 万")
        assert result["aml_risk_detected"] is True
        assert result["must_report_to_compliance"] is True

    def test_sensitive_leak_severity(self):
        """银行卡号 CVV 是 P0 严重, 手机号是 P1"""
        result = self.adapter.check_sensitive_leak("卡号 6225888888881234, CVV: 123")
        assert result["sensitive_leak"] is True
        # CVV 是 P0_critical
        assert any(v["severity"] == "P0_critical" for v in result["violations"])
