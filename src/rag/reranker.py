"""
Reranker (多信号加权) — 业界 Cross-Encoder Rerank 的 0 依赖替代
================================================================

为什么:
- 业界 Cross-Encoder Rerank: 用 BERT 等模型对 (query, doc) 对打分, 精度高但需重型模型
  代表: Cohere Rerank 3 / BGE Reranker v2 / m3e-reranker / Jina Reranker
- 本项目无大模型, 降级方案: 多信号加权 (multi-signal scoring)
  - 信号 1: 原始 retriever 分数 (RRF 或余弦)
  - 信号 2: question 关键词命中数
  - 信号 3: domain (业务领域) 匹配
  - 信号 4: tags (风险标签) 匹配
  - 信号 5: 业务上下文一致 (询问 L0 红线类 -> 优先 risk domain)
- 原理一致: 在召回后做精排 (re-rank), 用更多特征提升精度

业界对应:
- Cohere Rerank 3 (商业 API): cross-encoder 打分
- BGE Reranker v2-m3 (开源): cross-encoder 打分
- 本项目: 多特征加权打分 (无重型模型, 0 依赖)
"""
from __future__ import annotations

from typing import List, Dict, Optional, Set
import re


# L0 红线类 query 优先 domain (业务规则: 风险/欺诈/AML 优先 risk 域)
L0_DOMAINS = {"risk"}


class Reranker:
    """
    多信号 Reranker (业界 Cross-Encoder Rerank 的轻量替代)

    信号权重 (可调):
    - base_score: 原始 retriever 分数 (0.4)
    - keyword_match: question 关键词命中数 (0.2)
    - domain_match: domain 与 query 主题一致 (0.15)
    - tag_match: tags 与 query 关键词重叠 (0.15)
    - context_priority: L0 类 query 优先 risk domain (0.1)
    """

    # 银行业务分类启发式 (domain 推断)
    DOMAIN_KEYWORDS: Dict[str, List[str]] = {
        "credit_card": ["信用卡", "刷卡", "信用", "贷记卡", "账单"],
        "loan": ["贷款", "借款", "借钱", "信用贷", "抵押贷", "消费贷", "额度"],
        "account": ["账户", "余额", "查询", "一卡通", "储蓄卡"],
        "investment": ["理财", "投资", "收益", "财富", "基金", "存款"],
        "payment": ["转账", "汇款", "打款", "支付", "扣款"],
        "dcep": ["数字人民币", "DCEP", "央行数字货币"],
        "pension": ["养老金", "养老", "社保"],
        "gov": ["五险一金", "公积金", "政务", "民生"],
        "cross_border": ["外汇", "跨境", "境外", "海外"],
        "life": ["生活", "出行", "便民", "水电", "缴费"],
        "new_worker": ["骑手", "快递", "新就业", "灵活就业"],
        "service": ["客服", "投诉", "建议", "反馈", "服务"],
        "risk": ["诈骗", "盗刷", "被骗", "冻结", "异常", "洗钱", "AML"],
        "product": ["产品", "品牌", "新业务"],
    }

    # L0 红线 query 关键词
    L0_KEYWORDS = {"被骗", "盗刷", "诈骗", "冻结", "不明扣款", "给陌生人", "分多笔",
                   "化整为零", "假冒", "银监会", "公检法", "安全账户", "洗钱"}

    def __init__(self, knowledge_base: List[Dict]):
        self.knowledge_base = knowledge_base

    def rerank(
        self,
        query: str,
        candidates: List[Dict],
        top_k: Optional[int] = None,
    ) -> List[Dict]:
        """
        Rerank 候选 doc 列表

        Args:
            query: 原始 query
            candidates: 召回的候选 doc 列表
            top_k: 返回前 k 个

        Returns:
            重排后的 doc 列表
        """
        if not candidates:
            return []

        # 推断 query 主题 domain
        query_domain = self._infer_query_domain(query)
        is_l0_query = self._is_l0_query(query)

        scored = []
        for doc in candidates:
            score = self._score_doc(query, doc, query_domain, is_l0_query)
            scored.append({**doc, "rerank_score": round(score, 4)})

        # 降序
        scored.sort(key=lambda x: -x["rerank_score"])

        if top_k:
            scored = scored[:top_k]

        return scored

    def _score_doc(
        self,
        query: str,
        doc: Dict,
        query_domain: Optional[str],
        is_l0: bool,
    ) -> float:
        """
        多信号加权打分
        """
        score = 0.0

        # 信号 1: 原始 retriever 分数 (RRF 或余弦)
        base_score = max(
            doc.get("rrf_score", 0.0),
            doc.get("score", 0.0),
        )
        score += base_score * 0.4

        # 信号 2: question 关键词命中 (字符重叠率)
        question = doc.get("question", "")
        if question:
            q_tokens = set(self._char_ngrams(query, 2))
            d_tokens = set(self._char_ngrams(question, 2))
            if q_tokens:
                overlap = len(q_tokens & d_tokens) / len(q_tokens)
                score += overlap * 0.2

        # 信号 3: domain 匹配
        doc_domain = doc.get("domain", "")
        if query_domain and doc_domain == query_domain:
            score += 0.15
        elif query_domain and doc_domain:
            # 同组 domain 部分加分 (e.g. account <-> loan 都涉及资金)
            if self._is_related_domain(query_domain, doc_domain):
                score += 0.05

        # 信号 4: tags 匹配
        tags = doc.get("tags", [])
        if tags:
            query_lower = query.lower()
            tag_hits = sum(1 for t in tags if t in query_lower)
            if tag_hits > 0:
                score += min(tag_hits * 0.05, 0.15)

        # 信号 5: L0 上下文优先级
        if is_l0 and doc_domain == "risk":
            score += 0.1
        elif is_l0 and doc_domain != "risk":
            score -= 0.05  # L0 query 命中非 risk domain, 降权

        return score

    def _infer_query_domain(self, query: str) -> Optional[str]:
        """从 query 推断业务领域 (0 依赖启发式)"""
        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            if any(kw in query for kw in keywords):
                return domain
        return None

    def _is_l0_query(self, query: str) -> bool:
        """判断 query 是否 L0 红线类"""
        return any(kw in query for kw in self.L0_KEYWORDS)

    def _is_related_domain(self, d1: str, d2: str) -> bool:
        """判定两个 domain 是否相近 (银行业务关联)"""
        related = {
            "account": {"credit_card", "payment", "loan"},
            "credit_card": {"account", "payment"},
            "loan": {"account", "payment", "credit_card"},
            "investment": {"pension", "product"},
            "payment": {"account", "credit_card"},
            "dcep": {"payment"},
            "pension": {"investment"},
            "gov": {"pension", "life"},
            "cross_border": {"payment", "investment"},
            "life": {"gov", "payment"},
            "new_worker": {"loan", "life"},
            "service": {"account"},
            "risk": {"account", "credit_card", "payment"},
            "product": {"investment", "credit_card"},
        }
        return d2 in related.get(d1, set())

    @staticmethod
    def _char_ngrams(text: str, n: int) -> List[str]:
        if len(text) < n:
            return [text] if text else []
        return [text[i:i+n] for i in range(len(text) - n + 1)]


class RerankedRetriever:
    """
    完整检索 pipeline: 召回 (Multi-Query / Hybrid) + 精排 (Reranker)

    业界标准 pipeline (Elastic / Pinecone / Vespa):
    1. Recall (BM25 + Dense + Multi-Query)
    2. Rerank (Cross-Encoder / Cohere Rerank)
    3. Top-K
    """

    def __init__(
        self,
        knowledge_base: List[Dict],
        k: int = 5,
        recall_top_k: int = 20,
    ):
        """
        Args:
            knowledge_base: 知识库
            k: 最终 top_k
            recall_top_k: 召回阶段取多少给 reranker 精排
        """
        from .multi_query_retriever import MultiQueryRetriever
        self.knowledge_base = knowledge_base
        self.k = k
        self.recall_top_k = recall_top_k

        # 召回阶段: Multi-Query + Hybrid (业界最强组合)
        self.recaller = MultiQueryRetriever(knowledge_base, k=recall_top_k, use_hybrid=True)
        # 精排阶段: 多信号 Reranker
        self.reranker = Reranker(knowledge_base)

    def retrieve(self, query: str, top_k: Optional[int] = None) -> List[Dict]:
        """
        完整 pipeline: 召回 -> 精排 -> top_k
        """
        top_k = top_k or self.k

        # 1. 召回 (Multi-Query + Hybrid + RRF)
        candidates = self.recaller.retrieve(query, top_k=self.recall_top_k)

        # 2. 精排
        reranked = self.reranker.rerank(query, candidates, top_k=top_k)

        return reranked


def create_reranked_retriever(knowledge_base: List[Dict], k: int = 5) -> RerankedRetriever:
    """工厂函数"""
    return RerankedRetriever(knowledge_base, k=k)
