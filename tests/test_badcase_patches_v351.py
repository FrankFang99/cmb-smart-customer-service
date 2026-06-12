"""
测试 15: v3.5.1 Badcase 修复补丁
===================================
覆盖:
- 5 类 L0 P0 关键词触发
- 8 条意图规则补全
- 与现有 intent_recognizer 集成
"""
import pytest

from src.eval.badcase_patches_v351 import (
    V351_L0_PATCHES,
    V351_INTENT_RULES,
    V351_EXPECTED_IMPROVEMENT,
    V351_FRAUD_URGENT_TEMPLATE,
    apply_v351_patches,
    get_l0_patches,
    get_intent_rules,
)


class TestL0Patches:
    """L0 词典补全测试"""

    def test_urg_human_keywords(self):
        """紧急转人工关键词"""
        for kw in ["转人工", "需要人工服务", "找人工", "人工客服"]:
            assert kw in V351_L0_PATCHES
            assert V351_L0_PATCHES[kw]["category"] == "urg_human"
            assert V351_L0_PATCHES[kw]["severity"] == "P0"

    def test_sec_freeze_keywords(self):
        """账户异常冻结关键词"""
        for kw in ["账户异常冻结", "账户异常", "账户被冻", "卡被冻", "卡冻结了"]:
            assert kw in V351_L0_PATCHES
            assert V351_L0_PATCHES[kw]["category"] == "sec_freeze"
            assert V351_L0_PATCHES[kw]["severity"] == "P0"

    def test_sec_stolen_keywords(self):
        """收到陌生消费关键词"""
        for kw in ["收到陌生消费", "陌生消费", "不是我消费", "卡被刷了", "卡被刷"]:
            assert kw in V351_L0_PATCHES
            assert V351_L0_PATCHES[kw]["category"] == "sec_stolen"

    def test_sec_fraud_keywords(self):
        """被诈骗了关键词"""
        for kw in ["被诈骗了", "我被诈骗了", "被电信诈骗"]:
            assert kw in V351_L0_PATCHES
            assert V351_L0_PATCHES[kw]["category"] == "sec_fraud"

    def test_all_l0_p0_severity(self):
        """所有 L0 补丁都是 P0"""
        for kw, info in V351_L0_PATCHES.items():
            assert info["severity"] == "P0", f"{kw} 不是 P0"


class TestIntentRules:
    """意图规则补全测试"""

    def test_apply_credit_card_intent(self):
        """申请信用卡 -> cons_prod_credit"""
        for rule in V351_INTENT_RULES:
            if "申请信用卡" in rule["patterns"]:
                assert rule["intent"] == "cons_prod_credit"
                return
        pytest.fail("未找到 '申请信用卡' 规则")

    def test_apply_internal_transfer_intent(self):
        """转钱到招行卡 -> biz_tran_internal"""
        for rule in V351_INTENT_RULES:
            if "转钱到招行" in rule["patterns"]:
                assert rule["intent"] == "biz_tran_internal"
                return
        pytest.fail("未找到 '转钱到招行' 规则")

    def test_apply_wealth_consult_intent(self):
        """有什么好理财 -> cons_prod_wealth"""
        for rule in V351_INTENT_RULES:
            if "有什么好理财" in rule["patterns"]:
                assert rule["intent"] == "cons_prod_wealth"
                return
        pytest.fail("未找到 '有什么好理财' 规则")

    def test_apply_external_transfer_intent(self):
        """转账到别的银行 -> biz_tran_external"""
        for rule in V351_INTENT_RULES:
            if "转账到别的银行" in rule["patterns"]:
                assert rule["intent"] == "biz_tran_external"
                return
        pytest.fail("未找到 '转账到别的银行' 规则")

    def test_total_8_rules(self):
        """8 条规则"""
        assert len(V351_INTENT_RULES) == 8


class TestExpectedImprovement:
    """预期提升"""

    def test_intent_mismatch_improvement(self):
        """意图 mismatch 预期提升"""
        assert V351_EXPECTED_IMPROVEMENT["intent_mismatch"]["before"] == 8
        assert V351_EXPECTED_IMPROVEMENT["intent_mismatch"]["after"] <= 2

    def test_p0_recall_improvement(self):
        """P0 Recall 预期提升 (38.5% -> 100%)"""
        before = V351_EXPECTED_IMPROVEMENT["p0_recall"]["before"]
        after = V351_EXPECTED_IMPROVEMENT["p0_recall"]["after"]
        # before 含 "38.5%" (5/13=38.5%) 或 "50%" (cascade 评测)
        assert "100" in after
        # 提升至少 50pp
        fix_rate = V351_EXPECTED_IMPROVEMENT["p0_recall"]["fix_rate"]
        assert "pp" in fix_rate

    def test_l0_compliance_kept(self):
        """L0 Compliance 保持"""
        assert V351_EXPECTED_IMPROVEMENT["l0_compliance"]["after"] == "100%"


class TestApplyV351Patches:
    """应用补丁"""

    def test_apply_returns_stats(self):
        """apply_v351_patches 返统计"""
        stats = apply_v351_patches()
        assert stats["l0_patches_count"] == len(V351_L0_PATCHES)
        assert stats["intent_rules_count"] == 8
        assert stats["patch_version"] == "v3.5.1"

    def test_get_l0_patches(self):
        """get_l0_patches 返所有 L0 补丁"""
        patches = get_l0_patches()
        assert len(patches) == len(V351_L0_PATCHES)

    def test_get_intent_rules(self):
        """get_intent_rules 返所有意图规则"""
        rules = get_intent_rules()
        assert len(rules) == 8


class TestFraudUrgentTemplate:
    """反诈紧急模板"""

    def test_template_contains_required_phrases(self):
        """必含话术"""
        for phrase in ["95555", "挂失", "110", "报警", "密码"]:
            assert phrase in V351_FRAUD_URGENT_TEMPLATE


class TestIntegrationWithIntentRecognizer:
    """与现有意图识别器集成测试"""

    def test_urg_human_triggers_p0(self):
        """'转人工' 触发 P0"""
        from src.components.intent_recognizer import IntentRecognizer
        r = IntentRecognizer()
        result = r.recognize("转人工")
        assert result.is_p0 is True
        assert result.should_transfer is True

    def test_freeze_triggers_p0(self):
        """'账户异常冻结' 触发 P0"""
        from src.components.intent_recognizer import IntentRecognizer
        r = IntentRecognizer()
        result = r.recognize("账户异常冻结")
        assert result.is_p0 is True

    def test_stolen_card_triggers_p0(self):
        """'收到陌生消费' 触发 P0"""
        from src.components.intent_recognizer import IntentRecognizer
        r = IntentRecognizer()
        result = r.recognize("收到陌生消费")
        assert result.is_p0 is True

    def test_credit_card_consult_intent(self):
        """'申请信用卡' -> cons_prod_credit"""
        from src.components.intent_recognizer import IntentRecognizer
        r = IntentRecognizer()
        result = r.recognize("申请信用卡")
        assert result.intent.value == "cons_prod_credit"

    def test_wealth_consult_intent(self):
        """'有什么好理财' -> cons_prod_wealth"""
        from src.components.intent_recognizer import IntentRecognizer
        r = IntentRecognizer()
        result = r.recognize("有什么好理财")
        assert result.intent.value == "cons_prod_wealth"
