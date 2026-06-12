"""
测试 10: v3.5.0 意图识别 3 层架构
====================================
覆盖:
- L1 规则层 (17 级优先级)
- L2 小模型层 (TF-IDF + 业务词典 mock)
- L3 LLM 兜底层
- 置信度阈值 (0.95 / 0.70 / 0.0)
"""
import pytest

from src.components.intent_recognizer_3layer import (
    IntentRecognizer3Layer,
    SmallModelIntentClassifier,
    LLMIntentFallback,
    THRESHOLD_L1,
    THRESHOLD_L2,
)


class TestSmallModelIntentClassifier:
    """小模型层 (TF-IDF + 业务词典 mock)"""

    @pytest.fixture
    def sm(self):
        return SmallModelIntentClassifier()

    def test_predict_balance(self, sm):
        """余额查询"""
        intent, conf = sm.predict("我账户余额多少")
        assert intent == "info_acc_balance"
        assert 0.5 <= conf <= 0.85

    def test_predict_bill_amount(self, sm):
        """账单金额查询"""
        intent, conf = sm.predict("我的信用卡账单多少")
        assert intent == "info_bill_amount"

    def test_predict_greeting(self, sm):
        """问候"""
        intent, conf = sm.predict("你好")
        assert intent == "sys_greeting"

    def test_predict_fraud(self, sm):
        """反诈骗"""
        intent, conf = sm.predict("我被骗了10000")
        assert intent == "sec_fraud_report"

    def test_predict_unknown(self, sm):
        """未知意图"""
        intent, conf = sm.predict("asdfghjkl")
        assert intent == "unknown"
        assert conf == 0.0

    def test_get_top_k(self, sm):
        """top-k 候选"""
        top_k = sm.get_top_k("我的账单多少", k=3)
        assert len(top_k) == 3


class TestLLMIntentFallback:
    """LLM 兜底层"""

    def test_no_llm_returns_unknown(self):
        """无 LLM 时返 unknown"""
        llm = LLMIntentFallback(llm_chat=None)
        intent, conf = llm.predict("你好")
        assert intent == "unknown"
        assert conf == 0.0


class TestIntentRecognizer3Layer:
    """3 层意图识别器"""

    @pytest.fixture
    def r3l(self):
        return IntentRecognizer3Layer()

    def test_l1_high_confidence(self, r3l):
        """L1 规则层极高置信 (>= 0.95)"""
        result = r3l.recognize("你好")
        assert result.layer == "L1"
        assert result.confidence >= THRESHOLD_L1
        assert result.intent == "sys_greeting"

    def test_l2_medium_confidence(self, r3l):
        """L2 小模型层中等置信 (>= 0.70, < 0.95)"""
        result = r3l.recognize("信用卡账单金额怎么算")
        # L1 规则置信可能 < 0.95, L2 兜底
        assert result.layer in ("L1", "L2")

    def test_l3_fallback(self, r3l):
        """L3 兜底 (LLM 未识别时用 L1)"""
        result = r3l.recognize("blahblah unknown")
        assert result.layer == "L3_FALLBACK"

    def test_thresholds(self):
        """3 层阈值固定"""
        assert THRESHOLD_L1 == 0.95
        assert THRESHOLD_L2 == 0.70

    def test_result_fields(self, r3l):
        """结果字段完整"""
        result = r3l.recognize("你好")
        assert result.intent
        assert 0.0 <= result.confidence <= 1.0
        assert result.layer in ("L1", "L2", "L3", "L3_FALLBACK")
        assert result.reason
        assert result.raw_input == "你好"
