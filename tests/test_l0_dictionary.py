"""
测试 1: 银行业 L0 红线关键词词典
===================================
覆盖:
- AML 大额/化整为零 触发
- 反诈骗 高风险/假冒/给陌生人转 触发
- 越权访问 代查 触发
- 正常业务 不误触发
- 词典统计
"""
import pytest
from src.eval.banking_l0_dict import (
    check_l0, check_sensitive_in_text,
    AML_KEYWORDS, FRAUD_KEYWORDS, UNAUTHORIZED_KEYWORDS,
    get_dictionary_stats,
)


class TestL0Dictionary:
    """L0 红线词典测试"""

    def test_aml_large_amount_triggers(self):
        """AML 大额交易触发"""
        result = check_l0("我要转100万出去, 需要什么手续")
        assert result["l0_triggered"] is True
        assert any(c["category"] == "aml" for c in result["categories"])
        assert result["must_transfer_human"] is True

    def test_aml_structured_split_triggers(self):
        """AML 化整为零分笔触发 (反洗钱核心)"""
        result = check_l0("我想分多笔转出去，每次不到 5 万")
        assert result["l0_triggered"] is True
        cats = [c["sub_category"] for c in result["categories"]]
        assert "structured_split" in cats

    def test_fraud_high_risk_triggers(self):
        """反诈骗高风险 (被盗刷) 触发"""
        result = check_l0("我信用卡被盗刷了 5000 块")
        assert result["l0_triggered"] is True
        cats = [c["sub_category"] for c in result["categories"]]
        assert "fraud_high_risk" in cats

    def test_fraud_fake_official_triggers(self):
        """假冒公检法/银保监触发"""
        result = check_l0("银监会工作人员让我把钱转到安全账户")
        assert result["l0_triggered"] is True
        cats = [c["sub_category"] for c in result["categories"]]
        # 可能同时触发 fake_identity + fake_official_speech
        assert "fake_identity" in cats or "fake_official_speech" in cats

    def test_fraud_transfer_to_stranger_triggers(self):
        """给陌生人转账触发"""
        result = check_l0("我要给陌生人转 5 万块")
        assert result["l0_triggered"] is True
        cats = [c["sub_category"] for c in result["categories"]]
        assert "transfer_to_stranger" in cats

    def test_unauthorized_proxy_query_triggers(self):
        """代查他人账户触发"""
        result = check_l0("帮我老公查一下他账户里还有多少钱")
        assert result["l0_triggered"] is True
        cats = [c["sub_category"] for c in result["categories"]]
        assert "proxy_query" in cats

    def test_normal_business_not_triggered(self):
        """正常业务咨询不误触发"""
        result = check_l0("我信用卡还有多少钱要还")
        # "多少"和"钱"组合不应触发大额; 不能误判成诈骗/AML
        assert result["l0_triggered"] is False
        assert result["must_transfer_human"] is False

    def test_sensitive_info_detection(self):
        """敏感信息泄露检测"""
        # 银行卡号 16-19 位
        text = "我的卡号是 6225888888881234"
        violations = check_sensitive_in_text(text)
        types = [v["type"] for v in violations]
        assert "bank_card" in types

        # 手机号
        text = "我的手机是 13800138000"
        violations = check_sensitive_in_text(text)
        types = [v["type"] for v in violations]
        assert "phone" in types

    def test_dictionary_stats(self):
        """词典条数统计 (招行级词典 200+ 关键词)"""
        stats = get_dictionary_stats()
        assert stats["aml_total"] >= 50
        assert stats["fraud_total"] >= 100
        assert stats["unauthorized_total"] >= 30
        assert stats["l0_total"] >= 200  # 招行级要求
        assert stats["sensitive_total"] >= 5
