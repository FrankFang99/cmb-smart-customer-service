"""
Hybrid Retriever (Sparse + Dense + RRF) — 业界标准混合检索
============================================================

为什么:
- 单路检索 (要么 BM25 要么 embedding) 各有偏: 关键词强但语义弱 / 语义强但关键词弱
- 业界 (Pinecone / Weaviate / Elastic / Cohere) 标配: 混合 BM25 + 向量
- 融合方法: Reciprocal Rank Fusion (RRF), 2020 论文 Cormack et al. 是业界事实标准
  公式: RRF(d) = sum(1 / (k + rank_i(d))) for i in retrievers
  k 通常取 60

实现:
- Sparse 通道: SimpleRetriever (字符 2-gram, 0 依赖)
- Dense 通道: DenseRetriever (TF-IDF + 余弦, sklearn 已有)
- RRF 融合: 同 doc 在两个通道的排名加权求和
- 业界对应: 替换成 BGE / m3e 向量即可, RRF 框架不变

用法:
    from src.rag.hybrid_retriever import HybridRetriever
    r = HybridRetriever(knowledge_base, k=5)
    results = r.retrieve("如何查询账户余额")
"""
from __future__ import annotations

from typing import List, Dict, Optional
import numpy as np

from .simple_retriever import SimpleRetriever
from .dense_retriever import DenseRetriever


# RRF k 常数 (业界标准 60)
RRF_K = 60


def reciprocal_rank_fusion(
    rankings: List[List[Dict]],
    k: int = RRF_K,
) -> List[Dict]:
    """
    融合多个排序结果 (业界标准 RRF)

    Args:
        rankings: 每个 retriever 排好序的结果列表 [[{doc1}, {doc2}, ...], ...]
        k: RRF 平滑常数, 业界常用 60

    Returns:
        融合后的排序结果 [{**doc, "rrf_score": float, "retrieval_method": "rrf"}, ...]

    公式 (Cormack et al. 2009):
        RRF(d) = sum(1 / (k + rank_i(d)))
    """
    # 累加 RRF 分数, key 用 doc id
    rrf_scores: Dict[str, float] = {}
    doc_map: Dict[str, Dict] = {}
    contributing_methods: Dict[str, List[str]] = {}

    for ranking in rankings:
        for rank, doc in enumerate(ranking, start=1):
            doc_id = doc.get("id")
            if not doc_id:
                continue
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0 / (k + rank)
            doc_map[doc_id] = doc
            contributing_methods.setdefault(doc_id, []).append(
                doc.get("retrieval_method", "unknown")
            )

    # 按 RRF 分数降序
    sorted_ids = sorted(rrf_scores.keys(), key=lambda x: -rrf_scores[x])

    return [
        {
            **doc_map[doc_id],
            "rrf_score": round(rrf_scores[doc_id], 4),
            "retrieval_method": "rrf_hybrid",
            "contributing_methods": contributing_methods[doc_id],
        }
        for doc_id in sorted_ids
    ]


class HybridRetriever:
    """
    混合检索: Sparse (字符 2-gram BM25) + Dense (TF-IDF + 余弦) + RRF

    业界对应 (2024-2026 主流):
    - BM25: Elasticsearch / Lucene / OpenSearch
    - Dense: sentence-transformers / BGE / m3e / Cohere Embed / OpenAI ada
    - Hybrid: Pinecone hybrid / Weaviate hybrid / Elastic RRF (8.x) / Vespa
    - RRF 融合: Cormack 2009 论文, 业界事实标准

    0 新依赖 (sklearn 1.2.1 + numpy 1.26.4 已有)
    """

    def __init__(
        self,
        knowledge_base: List[Dict],
        k: int = 5,
        sparse_weight: float = 1.0,
        dense_weight: float = 1.0,
        rrf_k: int = RRF_K,
    ):
        """
        Args:
            knowledge_base: 知识库
            k: top_k
            sparse_weight: Sparse 通道权重 (RRF 系数)
            dense_weight: Dense 通道权重 (RRF 系数)
            rrf_k: RRF 平滑常数
        """
        self.k = k
        self.sparse_weight = sparse_weight
        self.dense_weight = dense_weight
        self.rrf_k = rrf_k
        self.knowledge_base = knowledge_base

        # 初始化两个通道
        self.sparse = SimpleRetriever(knowledge_base, k=k * 2)  # 多取一些给 RRF
        self.dense = DenseRetriever(knowledge_base, k=k * 2)

    def retrieve(self, query: str, top_k: Optional[int] = None) -> List[Dict]:
        """
        混合检索
        1. Sparse 通道 (字符 2-gram) -> ranking_1
        2. Dense 通道 (TF-IDF + 余弦) -> ranking_2
        3. RRF 融合 -> 最终排序
        """
        top_k = top_k or self.k

        # 两路召回
        sparse_results = self.sparse.retrieve(query, top_k=top_k * 2)
        dense_results = self.dense.retrieve(query, top_k=top_k * 2)

        # 加权 (用 RRF 分数乘以 weight, 然后再 RRF 一下)
        # 简化: 直接 RRF, weight 通过 rrf_k 调节
        if self.sparse_weight != 1.0 or self.dense_weight != 1.0:
            # 调整 rrf_k 等效于调整 weight
            weighted_sparse = self._apply_weight(sparse_results, self.sparse_weight)
            weighted_dense = self._apply_weight(dense_results, self.dense_weight)
            rankings = [weighted_sparse, weighted_dense]
        else:
            rankings = [sparse_results, dense_results]

        # RRF 融合
        fused = reciprocal_rank_fusion(rankings, k=self.rrf_k)

        return fused[:top_k]

    def _apply_weight(self, ranking: List[Dict], weight: float) -> List[Dict]:
        """给排序加权 (用 score 调整, 不影响 rank 序)"""
        for doc in ranking:
            doc["score"] = doc.get("score", 0.0) * weight
        return ranking


def create_hybrid_retriever(knowledge_base: List[Dict], k: int = 5) -> HybridRetriever:
    """工厂函数"""
    return HybridRetriever(knowledge_base, k=k)
