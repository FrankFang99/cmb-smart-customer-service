"""
测试 3: 意图识别器 (规则匹配覆盖度)
"""
import pytest
from src.components.intent_recognizer import IntentRecognizer, IntentType


class TestIntentRecognizer:
    """意图识别器测试"""

    def setup_method(self):
        self.r = IntentRecognizer()

    def test_balance_query(self):
        """余额查询"""
        result = self.r.recognize("我账户里还有多少钱")
        assert result.intent == IntentType.INFO_ACC_BALANCE

    def test_card_loss_p0(self):
        """卡片挂失是 P0 (必须转人工)"""
        result = self.r.recognize("我的信用卡丢了")
        assert result.intent == IntentType.BIZ_CARD_LOSS
        assert result.is_p0 is True
        assert result.should_transfer is True

    def test_loan_consult(self):
        """贷款咨询"""
        result = self.r.recognize("我想贷 30 万, 利率多少")
        assert result.intent.value.startswith("cons_prod_loan") or \
               result.intent == IntentType.CONS_PROD_LOAN

    def test_fraud_report_p0(self):
        """诈骗报案是 P0"""
        result = self.r.recognize("我刚才被骗了 2 万块")
        # fraud_report 走 P0 规则
        assert result.is_p0 is True

    def test_greeting_not_p0(self):
        """问候不是 P0"""
        result = self.r.recognize("你好")
        assert result.intent == IntentType.SYS_GREETING
        assert result.is_p0 is False

    def test_empty_input(self):
        """空输入"""
        result = self.r.recognize("")
        assert result.intent == IntentType.SYS_INVALID

    def test_multi_turn_context(self):
        """多轮对话: 第二轮提供 context 应该正确识别"""
        history = [
            {"role": "user", "content": "我想贷 30 万"},
            {"role": "assistant", "content": "好的, 您想贷多少? 利率 3.5% 起"},
        ]
        result = self.r.recognize("利率多少", context=history)
        # 即使是短句, 配合上下文也能识别
        assert result.intent.value != IntentType.SYS_INVALID.value
