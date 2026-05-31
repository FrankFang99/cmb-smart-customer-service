"""
简化检索器 - 不依赖sentence-transformers
用于评测环境
"""
from typing import List, Dict
import re


class SimpleRetriever:
    """
    简单检索器 - 基于关键词匹配
    用于评测环境，不依赖外部模型
    """

    def __init__(self, knowledge_base: List[Dict], k: int = 5):
        self.k = k
        self.knowledge_base = knowledge_base

    def retrieve(self, query: str, top_k: int = None) -> List[Dict]:
        """
        简单关键词匹配检索
        """
        top_k = top_k or self.k
        query_lower = query.lower()

        # 计算每个文档的匹配分数
        scores = []
        for i, item in enumerate(self.knowledge_base):
            score = 0.0
            question = item.get("question", "").lower()
            answer = item.get("answer", "").lower()
            tags = item.get("tags", [])
            intent = item.get("metadata", {}).get("intent", "")

            # 关键词匹配
            for keyword in query_lower.split():
                if len(keyword) > 1:
                    if keyword in question:
                        score += 3.0
                    if keyword in answer:
                        score += 1.0
                    if keyword in tags:
                        score += 2.0
                    if keyword in intent:
                        score += 2.0

            # 问题包含查询词
            if query_lower in question:
                score += 5.0

            # 完全匹配
            if query_lower.strip() == question:
                score += 10.0

            scores.append((i, score))

        # 排序
        scores.sort(key=lambda x: x[1], reverse=True)

        # 返回top_k结果
        return [
            {**self.knowledge_base[idx], "score": score, "retrieval_method": "keyword"}
            for idx, score in scores[:top_k] if score > 0
        ]


def create_retriever(knowledge_base: List[Dict], k: int = 5):
    """创建检索器工厂函数"""
    return SimpleRetriever(knowledge_base, k)