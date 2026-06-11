"""
Dense Retriever (TF-IDF + Cosine) — 业界 Dense Retrieval 的轻量版
====================================================================

为什么:
- 业界标准: 用 sentence-transformers (BGE / m3e) 把文本映射到 768 维向量, 余弦相似度检索
- 0 依赖替代: 用 sklearn TfidfVectorizer + cosine_similarity, 1.2.1 sklearn 已有
- 原理一致: 把文本编码成向量空间里的点, 用余弦夹角算相似度
- 业务场景适配: 银行业务术语集中在 565 条知识库, TF-IDF 词频向量比通用 embedding 更精准

业界对标 (2024-2026 主流):
- Cohere Embed v3 / OpenAI text-embedding-3 / BGE-M3 / m3e-large  -> 稠密向量 + 余弦
- 本项目 v3.3.5 替代: TF-IDF (词频向量) + 余弦
- 局限: 没法处理同义词 (embedding 能, TF-IDF 不能), 但银行业务术语固定, TF-IDF 够用

用法:
    from src.rag.dense_retriever import DenseRetriever
    r = DenseRetriever(knowledge_base, k=5)
    results = r.retrieve("如何查询账户余额")
"""
from __future__ import annotations

from typing import List, Dict, Optional
import re


# 中文文本预处理: 简单分词 (字符 1-gram + 2-gram 混合)
# 业界做法: jieba 精确分词 + 自定义词典; 本项目 0 依赖, 用正则切分
def _tokenize_cn(text: str) -> List[str]:
    """
    简易中文分词: 字符 + 2-gram 混合
    业界对比: jieba.cut (基于 CRF) / sentencepiece (BPE) / BPE tokenizer
    本项目 0 依赖, 字符 + 2-gram 兼顾词频 + 子词信息
    """
    if not text:
        return []
    text = text.strip()
    tokens = []

    # 1-gram (单字)
    tokens.extend(list(text))

    # 2-gram (字符对, 业界子词单元)
    for i in range(len(text) - 1):
        tokens.append(text[i:i+2])

    return tokens


def _build_doc_text(item: Dict) -> str:
    """构建 doc 文本: question + answer + tags + domain_zh + intent"""
    parts = [
        item.get("question", ""),
        item.get("answer", ""),
        " ".join(item.get("tags", [])),
        item.get("domain_zh", ""),
        item.get("metadata", {}).get("intent", ""),
    ]
    return " ".join(filter(None, parts))


class DenseRetriever:
    """
    TF-IDF + Cosine 稠密检索 (业界 Dense Retrieval 的轻量版)

    实现:
    1. 把知识库每条 doc 编码成 TF-IDF 词频向量 (L2 归一化)
    2. query 同样编码
    3. cos(theta) = dot(q, d) / (|q| * |d|), sklearn 0 依赖内建

    业界对应:
    - 稠密向量: TF-IDF 稀疏向量 (维度 = 词表大小, ~10000)
    - 余弦相似度: sklearn.metrics.pairwise.cosine_similarity
    - 近邻检索: 穷举 (565 条规模足够); 上规模用 faiss / annoy / hnswlib
    """

    def __init__(self, knowledge_base: List[Dict], k: int = 5):
        self.k = k
        self.knowledge_base = knowledge_base

        # 延迟 import, 避免启动时拉 sklearn
        from sklearn.feature_extraction.text import TfidfVectorizer

        # 构建语料 (每条 doc 一个文本)
        corpus = [_build_doc_text(item) for item in knowledge_base]
        self._tokenized_corpus = [_tokenize_cn(t) for t in corpus]

        # 训练 TF-IDF (用自定义 tokenizer 保持一致)
        self.vectorizer = TfidfVectorizer(
            tokenizer=lambda x: x,  # 我们已经分词过了
            preprocessor=lambda x: x,
            token_pattern=None,     # 禁用默认正则
            lowercase=False,         # 中文不 lower
            max_features=10000,      # 词表上限
            min_df=1,                # 最小文档频率
            sublinear_tf=True,       # 业界标配: 1+log(tf) 抑制高频词
        )
        # sklearn 要求 corpus 是字符串列表, 但 tokenizer 返回列表
        # 解决: corpus 用空格分隔的分词结果
        corpus_joined = [" ".join(tokens) for tokens in self._tokenized_corpus]
        self.doc_vectors = self.vectorizer.fit_transform(corpus_joined)

    def retrieve(self, query: str, top_k: Optional[int] = None) -> List[Dict]:
        """
        检索: query 向量化 -> 余弦相似度 -> top_k
        """
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np

        top_k = top_k or self.k

        # query 分词 + 向量化
        query_tokens = _tokenize_cn(query)
        query_joined = " ".join(query_tokens)
        query_vec = self.vectorizer.transform([query_joined])

        # 余弦相似度 (TF-IDF 已 L2 归一化, cos = dot)
        sims = cosine_similarity(query_vec, self.doc_vectors).flatten()

        # top_k 索引 (按相似度降序)
        top_indices = np.argsort(-sims)[:top_k]

        # 过滤 score > 0
        results = []
        for idx in top_indices:
            score = float(sims[idx])
            if score <= 0:
                continue
            results.append({
                **self.knowledge_base[idx],
                "score": round(score, 4),
                "retrieval_method": "tfidf_cosine",
            })

        return results


def create_dense_retriever(knowledge_base: List[Dict], k: int = 5) -> DenseRetriever:
    """工厂函数"""
    return DenseRetriever(knowledge_base, k)
