"""
测试 7: v3.4.0-b 知识库分类管理
=================================
覆盖:
- 3 类库分类 (doc_kb / faq_kb / biz_db)
- 分类规则 (按 category / domain)
- Chunking 策略
- 业务数据库 mock 查询
"""
import pytest

from src.rag.knowledge_base_v2 import (
    KnowledgeBaseClassifier,
    BizDBMock,
    CHUNKING_STRATEGIES,
    get_classifier,
    get_biz_db,
    _classify_chunk_strategy,
)


class TestChunkingStrategies:
    """Chunking 策略测试"""

    def test_strategies_complete(self):
        """6 种策略都存在"""
        expected = {"smart", "by_heading", "by_row", "qa_pair", "full_table", "by_endpoint", "by_dialogue"}
        assert set(CHUNKING_STRATEGIES.keys()) == expected

    def test_strategy_descriptions_not_empty(self):
        """每个策略有描述"""
        for name, desc in CHUNKING_STRATEGIES.items():
            assert desc
            assert len(desc) > 5

    def test_classify_chunk_strategy(self):
        """根据 entry 字段推断 chunk 策略"""
        # consult 类 -> qa_pair
        assert _classify_chunk_strategy({"category": "consult", "domain": "loan"}) == "qa_pair"
        # marketing 类 -> qa_pair
        assert _classify_chunk_strategy({"category": "marketing", "domain": "credit_card"}) == "qa_pair"
        # query 类 -> by_heading
        assert _classify_chunk_strategy({"category": "query", "domain": "account"}) == "by_heading"
        # risk 类 -> smart
        assert _classify_chunk_strategy({"category": "risk", "domain": "risk"}) == "smart"


class TestKnowledgeBaseClassifier:
    """知识库分类器测试"""

    @pytest.fixture
    def classifier(self):
        return get_classifier()

    def test_total_equals_sum(self, classifier):
        """3 类库之和 = 565 (v2.0 总量)"""
        s = classifier.stats()
        assert s["by_class"]["doc_kb"] + s["by_class"]["faq_kb"] + s["by_class"]["biz_db_entries"] == 565

    def test_faq_kb_contains_consult_and_marketing(self, classifier):
        """FAQ 库含 consult/marketing 类"""
        for entry in classifier.faq_kb[:10]:
            assert entry["category"] in ("consult", "marketing")

    def test_biz_db_contains_query_with_business_domain(self, classifier):
        """业务数据库含 query 类 + 业务 domain"""
        for entry in classifier.biz_db_entries[:10]:
            assert entry["category"] == "query"
            assert entry["domain"] in ("account", "credit_card", "payment", "life")

    def test_doc_kb_contains_other(self, classifier):
        """文档库含其他类 (risk/transaction/service_transfer)"""
        cats = {e["category"] for e in classifier.doc_kb}
        assert "risk" in cats or "transaction" in cats or "service_transfer" in cats

    def test_chunk_strategy_assigned(self, classifier):
        """每条 entry 都有 chunk_strategy 字段"""
        all_entries = classifier.faq_kb + classifier.doc_kb + classifier.biz_db_entries
        for entry in all_entries[:20]:
            assert "chunk_strategy" in entry
            assert entry["chunk_strategy"] in CHUNKING_STRATEGIES

    def test_get_by_chunk_strategy(self, classifier):
        """按 chunk 策略查"""
        qa_pair = classifier.get_by_chunk_strategy("qa_pair")
        assert len(qa_pair) > 0
        for e in qa_pair:
            assert e["chunk_strategy"] == "qa_pair"

    def test_get_by_domain(self, classifier):
        """按 domain 查"""
        loan = classifier.get_by_domain("loan")
        assert len(loan) == 50  # v2.0 loan 域 50 条
        for e in loan:
            assert e["domain"] == "loan"

    def test_stats(self, classifier):
        """统计字段完整"""
        s = classifier.stats()
        for k in ["total", "by_class", "by_chunk_strategy", "by_domain", "by_category"]:
            assert k in s
        assert s["total"] == 565


class TestBizDBMock:
    """业务数据库 mock 测试"""

    @pytest.fixture
    def db(self):
        return get_biz_db()

    def test_query_bill_amount(self, db):
        """查询账单金额"""
        bill = db.query_bill_amount("C001")
        assert bill is not None
        assert bill["amount"] == 12345.67
        assert bill["due_date"] == "2026-07-05"
        assert bill["status"] == "待还款"

    def test_query_bill_amount_nonexistent(self, db):
        """不存在客户返 None"""
        assert db.query_bill_amount("C999") is None

    def test_query_transaction_record(self, db):
        """查询交易记录"""
        records = db.query_transaction_record("C001")
        assert len(records) >= 1
        for r in records:
            assert "amount" in r
            assert "merchant" in r
            assert "date" in r

    def test_query_logistics(self, db):
        """查询物流"""
        log = db.query_logistics("C001")
        assert log is not None
        assert log["carrier"] == "顺丰"
        assert log["status"] == "在途"

    def test_query_product(self, db):
        """查询产品"""
        p = db.query_product("P_CMBC_CREDIT_001")
        assert p is not None
        assert p["name"] == "招商银行 Young 卡"
        assert p["type"] == "credit_card"

    def test_query_product_nonexistent(self, db):
        """不存在产品返 None"""
        assert db.query_product("P_NONEXIST") is None

    def test_query_credit_cards(self, db):
        """查询所有信用卡"""
        cards = db.query_credit_cards()
        assert len(cards) >= 1
        for c in cards:
            assert c["type"] == "credit_card"

    def test_query_wealth_products(self, db):
        """查询所有理财"""
        wealths = db.query_wealth_products()
        assert len(wealths) >= 1
        for w in wealths:
            assert w["type"] == "wealth"
            # 投资类产品必须有预期收益和风险等级
            assert "expected_annual_return" in w
            assert "risk_level" in w

    def test_format_bill_answer(self, db):
        """格式化账单回答"""
        ans = db.format_bill_answer("C001")
        assert "12345.67" in ans
        assert "2026-07-05" in ans
        assert "95555" in ans

    def test_format_logistics_answer(self, db):
        """格式化物流回答"""
        ans = db.format_logistics_answer("C001")
        assert "顺丰" in ans
        assert "在途" in ans

    def test_format_bill_answer_nonexistent(self, db):
        """不存在客户返合规话术"""
        ans = db.format_bill_answer("C999")
        assert "未查询到" in ans
