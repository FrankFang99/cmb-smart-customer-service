"""
测试 14: v3.5.1 BGE-Reranker mock
===================================
覆盖:
- 5 信号打分
- 关键词重叠
- 语义相似度
- 位置权重
- 业务域匹配
- 长度归一化
- Rerank 排序
"""
import pytest

from src.rag.bge_reranker_mock import (
    BGERerankerMock,
    RERANKER_COMPARISON,
    get_bge_reranker_mock,
    _tokenize,
)


class TestBGETokenize:
    """BGE 分词测试"""

    def test_basic(self):
        """基本分词"""
        tokens = _tokenize("信用卡账单")
        assert "信用" in tokens
        assert "用卡" in tokens
        assert "卡账" in tokens
        assert "账单" in tokens

    def test_stop_words(self):
        """停用词过滤"""
        tokens = _tokenize("的 了")
        # 停用词应被过滤
        for t in tokens:
            assert t not in {"的", "了"}


class TestBGERerankerMock:
    """BGE-Reranker mock 测试"""

    @pytest.fixture
    def reranker(self):
        return get_bge_reranker_mock()

    @pytest.fixture
    def candidates(self):
        return [
            {"question": "如何查询账户余额", "answer": "登录招行App 我的 账户余额", "domain": "account"},
            {"question": "信用卡激活", "answer": "登录App 卡片管理 卡片激活", "domain": "credit_card"},
            {"question": "怎么贷款", "answer": "招行信用贷最高 50 万", "domain": "loan"},
            {"question": "理财产品推荐", "answer": "朝朝宝 日日盈", "domain": "investment"},
        ]

    def test_rerank_balance(self, reranker, candidates):
        """余额 query 排第一"""
        ranked = reranker.rerank("我账户余额多少", candidates, top_k=2)
        assert ranked[0][0]["domain"] == "account"

    def test_rerank_credit(self, reranker, candidates):
        """信用卡 query 排第一"""
        ranked = reranker.rerank("信用卡怎么激活", candidates, top_k=2)
        assert ranked[0][0]["domain"] == "credit_card"

    def test_rerank_loan(self, reranker, candidates):
        """贷款 query 排第一"""
        ranked = reranker.rerank("怎么借钱", candidates, top_k=2)
        assert ranked[0][0]["domain"] == "loan"

    def test_top_k(self, reranker, candidates):
        """top_k 限制"""
        ranked = reranker.rerank("信用卡", candidates, top_k=2)
        assert len(ranked) == 2

    def test_empty_candidates(self, reranker):
        """空候选"""
        ranked = reranker.rerank("test", [], top_k=5)
        assert ranked == []

    def test_score_range(self, reranker, candidates):
        """分数 0-1 范围"""
        ranked = reranker.rerank("信用卡", candidates, top_k=4)
        for doc, score in ranked:
            assert 0.0 <= score <= 1.0

    def test_weights_sum_to_one(self, reranker):
        """权重和为 1"""
        total = sum(reranker.WEIGHTS.values())
        assert abs(total - 1.0) < 0.001

    def test_stats(self, reranker):
        """BGE 选型说明完整"""
        s = reranker.stats()
        assert s["model"] == "BGE Reranker v2-m3 (mock)"
        assert len(s["rationale"]) == 5
        assert "v4_0_upgrade_path" in s


class TestRerankerComparison:
    """Reranker 对比表"""

    def test_bge_info(self):
        """BGE 选型信息"""
        bge = RERANKER_COMPARISON["BGE Reranker v2-m3"]
        assert bge["vendor"] == "智源 (BAAI)"
        assert bge["type"] == "cross-encoder"
        assert "招行_instance" in bge

    def test_project_mock_in_comparison(self):
        """本项目 mock 在对比表里"""
        mock = RERANKER_COMPARISON["本项目 (v3.5.1 mock)"]
        assert mock["size"] == "0 参数"
        assert mock["cost"] == "0 依赖"

    def test_comparison_has_4_rerankers(self):
        """对比表 4 个 Reranker"""
        assert len(RERANKER_COMPARISON) == 4
