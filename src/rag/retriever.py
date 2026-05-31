"""
混合检索器
结合向量检索 + BM25 关键词检索
"""
from typing import List, Dict, Tuple
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from sentence_transformers import SentenceTransformer
import numpy as np


class HybridRetriever:
    """
    混合检索器
    - 向量检索：语义相似度
    - BM25：关键词匹配
    - 融合：RRF 算法
    """

    def __init__(self, knowledge_base: List[Dict], k: int = 5):
        self.k = k
        self.knowledge_base = knowledge_base
        self._init_vector_store()
        self._init_bm25()

    def _init_vector_store(self):
        """初始化向量库"""
        # 使用 sentence-transformers 本地模型
        texts = [item["answer"] for item in self.knowledge_base]
        metadatas = [
            {
                "id": item["id"],
                "question": item["question"],
                "category": item["category"],
                "intent": item.get("metadata", {}).get("intent", "unknown")
            }
            for item in self.knowledge_base
        ]

        # 创建 Chroma 向量库
        # 使用本地 sentence-transformers 模型
        self.embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        embeddings = self.embedding_model.encode(texts)

        # 存储向量和元数据
        self.documents = texts
        self.metadatas = metadatas

    def _init_bm25(self):
        """初始化 BM25 索引"""
        # 简单 BM25 实现
        from collections import defaultdict
        import math

        self.bm25_index = defaultdict(dict)
        self.doc_lengths = []
        self.avg_doc_length = 0

        # 分词
        def tokenize(text):
            return list(text)  # 简单按字分词

        # 构建索引
        for i, doc in enumerate(self.documents):
            tokens = tokenize(doc)
            self.doc_lengths.append(len(tokens))

            for token in set(tokens):
                self.bm25_index[token][i] = tokens.count(token)

        self.avg_doc_length = sum(self.doc_lengths) / len(self.doc_lengths) if self.doc_lengths else 1

    def vector_search(self, query: str) -> List[Tuple[int, float]]:
        """向量检索"""
        query_embedding = self.embedding_model.encode([query])[0]

        # 计算余弦相似度
        scores = []
        for i, doc_emb in enumerate(self._get_all_embeddings()):
            cos_sim = np.dot(query_embedding, doc_emb) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(doc_emb) + 1e-10
            )
            scores.append((i, float(cos_sim)))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:self.k]

    def _get_all_embeddings(self):
        """获取所有文档的嵌入向量（缓存）"""
        if not hasattr(self, '_cached_embeddings'):
            self._cached_embeddings = self.embedding_model.encode(self.documents)
        return self._cached_embeddings

    def bm25_search(self, query: str, k: int = None) -> List[Tuple[int, float]]:
        """BM25 检索"""
        k = k or self.k
        k1, b = 1.5, 0.75

        tokens = list(query)  # 简单按字分词
        doc_scores = {i: 0.0 for i in range(len(self.documents))}

        for token in tokens:
            if token in self.bm25_index:
                for doc_id, freq in self.bm25_index[token].items():
                    idf = math.log((len(self.documents) - len(self.bm25_index[token]) + 0.5) /
                                   (len(self.bm25_index[token]) + 0.5) + 1)
                    doc_freq = freq
                    score = idf * (doc_freq * (k1 + 1)) / (doc_freq + k1 * (1 - b + b * self.doc_lengths[doc_id] / self.avg_doc_length))
                    doc_scores[doc_id] += score

        scores = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
        return scores[:k]

    def retrieve(self, query: str, top_k: int = None) -> List[Dict]:
        """
        混合检索
        使用 RRF (Reciprocal Rank Fusion) 融合向量和 BM25 结果
        """
        top_k = top_k or self.k

        # 分别检索
        vector_results = self.vector_search(query)
        bm25_results = self.bm25_search(query)

        # RRF 融合
        rrf_scores = {}
        k_rrf = 60  # RRF 参数

        for rank, (doc_id, score) in enumerate(vector_results):
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1 / (k_rrf + rank + 1)

        for rank, (doc_id, score) in enumerate(bm25_results):
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1 / (k_rrf + rank + 1)

        # 排序
        sorted_results = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        # 返回完整信息
        return [
            {
                **self.knowledge_base[doc_id],
                "score": score,
                "retrieval_method": "hybrid"
            }
            for doc_id, score in sorted_results
        ]


def create_retriever(knowledge_base: List[Dict], k: int = 5) -> HybridRetriever:
    """创建检索器工厂函数"""
    return HybridRetriever(knowledge_base, k)