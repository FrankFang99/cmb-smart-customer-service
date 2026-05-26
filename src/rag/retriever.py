"""
娣峰悎妫€绱㈠櫒
缁撳悎鍚戦噺妫€绱?+ BM25 鍏抽敭璇嶆绱?"""
from typing import List, Dict, Tuple
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import numpy as np


class HybridRetriever:
    """
    娣峰悎妫€绱㈠櫒
    - 鍚戦噺妫€绱細璇箟鐩镐技搴?    - BM25锛氬叧閿瘝鍖归厤
    - 铻嶅悎锛歊RF 绠楁硶
    """

    def __init__(self, knowledge_base: List[Dict], k: int = 5):
        self.k = k
        self.knowledge_base = knowledge_base
        self._init_vector_store()
        self._init_bm25()

    def _init_vector_store(self):
        """鍒濆鍖栧悜閲忓簱"""
        # 浣跨敤 sentence-transformers 鏈湴妯″瀷
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

        # 鍒涘缓 Chroma 鍚戦噺搴?        # 浣跨敤鏈湴 sentence-transformers 妯″瀷
        self.embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        embeddings = self.embedding_model.encode(texts)

        # 瀛樺偍鍚戦噺鍜屽厓鏁版嵁
        self.documents = texts
        self.metadatas = metadatas

    def _init_bm25(self):
        """鍒濆鍖?BM25 绱㈠紩"""
        # 绠€鍗?BM25 瀹炵幇
        from collections import defaultdict
        import math

        self.bm25_index = defaultdict(dict)
        self.doc_lengths = []
        self.avg_doc_length = 0

        # 鍒嗚瘝
        def tokenize(text):
            return list(text)  # 绠€鍗曟寜瀛楀垎璇?
        # 鏋勫缓绱㈠紩
        for i, doc in enumerate(self.documents):
            tokens = tokenize(doc)
            self.doc_lengths.append(len(tokens))

            for token in set(tokens):
                self.bm25_index[token][i] = tokens.count(token)

        self.avg_doc_length = sum(self.doc_lengths) / len(self.doc_lengths) if self.doc_lengths else 1

    def vector_search(self, query: str) -> List[Tuple[int, float]]:
        """鍚戦噺妫€绱?""
        query_embedding = self.embedding_model.encode([query])[0]

        # 璁＄畻浣欏鸡鐩镐技搴?        scores = []
        for i, doc_emb in enumerate(self._get_all_embeddings()):
            cos_sim = np.dot(query_embedding, doc_emb) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(doc_emb) + 1e-10
            )
            scores.append((i, float(cos_sim)))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:self.k]

    def _get_all_embeddings(self):
        """鑾峰彇鎵€鏈夋枃妗ｇ殑宓屽叆鍚戦噺锛堢紦瀛橈級"""
        if not hasattr(self, '_cached_embeddings'):
            self._cached_embeddings = self.embedding_model.encode(self.documents)
        return self._cached_embeddings

    def bm25_search(self, query: str, k: int = None) -> List[Tuple[int, float]]:
        """BM25 妫€绱?""
        k = k or self.k
        k1, b = 1.5, 0.75

        tokens = list(query)  # 绠€鍗曟寜瀛楀垎璇?        doc_scores = {i: 0.0 for i in range(len(self.documents))}

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
        娣峰悎妫€绱?        浣跨敤 RRF (Reciprocal Rank Fusion) 铻嶅悎鍚戦噺鍜?BM25 缁撴灉
        """
        top_k = top_k or self.k

        # 鍒嗗埆妫€绱?        vector_results = self.vector_search(query)
        bm25_results = self.bm25_search(query)

        # RRF 铻嶅悎
        rrf_scores = {}
        k_rrf = 60  # RRF 鍙傛暟

        for rank, (doc_id, score) in enumerate(vector_results):
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1 / (k_rrf + rank + 1)

        for rank, (doc_id, score) in enumerate(bm25_results):
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1 / (k_rrf + rank + 1)

        # 鎺掑簭
        sorted_results = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        # 杩斿洖瀹屾暣淇℃伅
        return [
            {
                **self.knowledge_base[doc_id],
                "score": score,
                "retrieval_method": "hybrid"
            }
            for doc_id, score in sorted_results
        ]


def create_retriever(knowledge_base: List[Dict], k: int = 5) -> HybridRetriever:
    """鍒涘缓妫€绱㈠櫒宸ュ巶鍑芥暟"""
    return HybridRetriever(knowledge_base, k)