"""
测试 12: v3.5.0 幻觉检测
==========================
覆盖:
- 关键词重叠检测 (NLI mock)
- 数字/事实校验
- 禁止词检测
- 综合幻觉检测器
"""
import pytest

from src.agent.hallucination_detector import (
    HallucinationDetector,
    KeywordOverlapChecker,
    NumberFactChecker,
    PhraseForbiddenChecker,
    FORBIDDEN_PHRASES,
    STOP_WORDS,
    _tokenize,
    get_hallucination_detector,
)


class TestTokenize:
    """分词测试"""

    def test_basic_tokenize(self):
        """基本分词"""
        tokens = _tokenize("您的信用卡账单金额为 12345.67 元")
        assert "信用卡" in tokens or any("信用卡" in t for t in tokens)
        assert "账单" in tokens or any("账单" in t for t in tokens)

    def test_stop_words_filtered(self):
        """停用词过滤"""
        tokens = _tokenize("的 了吗")
        # 停用词应被过滤
        for t in tokens:
            assert t not in {"的", "了", "吗"} or len(t) > 1

    def test_2gram(self):
        """2-gram 提取"""
        tokens = _tokenize("余额查询")
        assert "余额" in tokens
        assert "额查" in tokens or any("额" in t for t in tokens)


class TestKeywordOverlapChecker:
    """关键词重叠检测"""

    @pytest.fixture
    def checker(self):
        return KeywordOverlapChecker(threshold=0.3)

    def test_high_overlap(self, checker):
        """高重叠"""
        r = checker.check("您的信用卡账单金额为 12345 元", "您的账单金额 12345 元")
        assert r["supported"] is True
        assert r["score"] > 0.3

    def test_low_overlap(self, checker):
        """低重叠"""
        r = checker.check("您的账户余额为 100 万", "招行信用卡账单查询方式")
        assert r["supported"] is False
        assert r["score"] < 0.3

    def test_empty_answer(self, checker):
        """空答案"""
        r = checker.check("", "招行信用卡账单查询")
        assert r["supported"] is False
        assert r["score"] == 0.0


class TestNumberFactChecker:
    """数字事实校验"""

    @pytest.fixture
    def checker(self):
        return NumberFactChecker()

    def test_supported_numbers(self, checker):
        """数字在证据中"""
        r = checker.check("您的账单金额 12345.67 元", "您的账单金额 12345.67 元")
        assert r["supported"] is True
        assert r["unsupported_numbers"] == []

    def test_unsupported_number(self, checker):
        """数字不在证据中"""
        r = checker.check("您的账单金额 99999 元", "您的账单金额 12345 元")
        assert r["supported"] is False
        assert "99999" in r["unsupported_numbers"]

    def test_no_numbers(self, checker):
        """无数字"""
        r = checker.check("您的账单已出", "请登录 App 查看")
        assert r["supported"] is True


class TestPhraseForbiddenChecker:
    """禁止词检测"""

    @pytest.fixture
    def checker(self):
        return PhraseForbiddenChecker()

    def test_no_forbidden(self, checker):
        """无禁止词"""
        r = checker.check("您的账单金额为 12345 元")
        assert r["supported"] is True
        assert r["forbidden_phrases"] == []

    def test_ai_phrases(self, checker):
        """AI 类禁止词"""
        r = checker.check("作为 AI, 我无法回答")
        assert r["supported"] is False
        assert "作为 AI" in r["forbidden_phrases"]

    def test_finance_guarantee(self, checker):
        """金融保证类禁止词"""
        r = checker.check("保本保息 100% 安全")
        assert r["supported"] is False
        assert len(r["forbidden_phrases"]) > 0

    def test_forbidden_phrases_complete(self):
        """禁止词表完整"""
        for p in ["我无法", "作为 AI", "保本保息", "100% 安全"]:
            assert p in FORBIDDEN_PHRASES


class TestHallucinationDetector:
    """综合幻觉检测器"""

    @pytest.fixture
    def detector(self):
        return get_hallucination_detector()

    def test_no_hallucination(self, detector):
        """无幻觉"""
        r = detector.detect("您的账单金额 12345.67 元", "您的账单金额 12345.67 元")
        assert r["is_hallucination"] is False
        assert r["action"] == "pass"
        assert r["score"] < 0.2

    def test_warn_fake_number(self, detector):
        """假数字 (warn)"""
        r = detector.detect("您的账单金额 99999 元", "您的账单金额 12345 元")
        assert r["action"] in ("warn", "fallback_template")
        assert r["score"] >= 0.2

    def test_warn_ai_phrase(self, detector):
        """AI 禁用词 (warn)"""
        r = detector.detect("作为 AI, 我无法回答", "")
        assert r["action"] in ("warn", "fallback_template")

    def test_fallback_finance_guarantee(self, detector):
        """金融保证类 (fallback_template)"""
        r = detector.detect("保本保息 100% 安全", "理财非存款")
        assert r["action"] == "fallback_template"
        assert r["is_hallucination"] is True
        assert r["score"] >= 0.5

    def test_all_checks_present(self, detector):
        """所有 check 都存在"""
        r = detector.detect("test", "evidence")
        for k in ("overlap", "number", "forbidden"):
            assert k in r["checks"]
