"""
简化检索器 - 不依赖 sentence-transformers / jieba
用于评测环境 + 面试作品集 (0 依赖, 中文 BM25 风格)

v3.3.4 增强 (P1-新-A 修复):
- 中文字符 2-gram 提取 (替代 jieba 分词, 解决 "分期手续费" 短词匹配)
- query 短词 (>=2 字) 在 question/answer 里 substring 命中
- 多字段加权 (question > tags > answer > intent)
- 0 外部依赖 (符合面试作品集定位)
"""
from typing import List, Dict
import re


# 银行业务高频词停用词 (避免 "如何" "怎么" 这种没区分度的词拉高分数)
STOP_WORDS = {
    "如何", "怎么", "怎样", "什么", "哪些", "哪里", "哪个", "这个", "那个",
    "我要", "我需要", "我想", "请问", "您好", "你好", "麻烦", "一下",
    "的", "了", "是", "在", "和", "与", "或", "及",
    "吗", "呢", "啊", "哦", "嗯", "吧", "呀",
    "我", "你", "他", "她", "它", "们",
}


def tokenize_cn(text: str, min_len: int = 2) -> List[str]:
    """
    简易中文分词: 滑动窗口 2-gram + 过滤停用词
    例: "信用卡分期手续费" -> ["信用", "用卡", "卡分", "分期", "期手", "手续", "续费"]
    避免依赖 jieba, 0 安装成本
    """
    if not text:
        return []
    text = text.strip()
    tokens = set()
    # 2-gram
    for i in range(len(text) - 1):
        gram = text[i:i+2]
        if gram not in STOP_WORDS and not all(c in STOP_WORDS for c in gram):
            tokens.add(gram)
    # 3-gram (覆盖更长关键词)
    for i in range(len(text) - 2):
        gram = text[i:i+3]
        if gram not in STOP_WORDS:
            tokens.add(gram)
    return [t for t in tokens if len(t) >= min_len]


class SimpleRetriever:
    """
    简单检索器 - 基于关键词 + 中文 2-gram 匹配
    用于评测环境, 0 外部依赖
    """

    def __init__(self, knowledge_base: List[Dict], k: int = 5):
        self.k = k
        self.knowledge_base = knowledge_base
        # 预计算每个文档的 tokens (提速)
        self._doc_tokens = []
        for item in knowledge_base:
            text = (item.get("question", "") + " " + item.get("answer", "") + " " +
                    " ".join(item.get("tags", [])) + " " +
                    item.get("metadata", {}).get("intent", "") + " " +
                    item.get("domain_zh", ""))
            self._doc_tokens.append(tokenize_cn(text))

    def retrieve(self, query: str, top_k: int = None) -> List[Dict]:
        """
        检索 - 多字段加权 + 中文 2-gram
        """
        top_k = top_k or self.k
        query_lower = query.lower()

        # query 分词
        query_tokens = set(tokenize_cn(query))

        scores = []
        for i, item in enumerate(self.knowledge_base):
            score = 0.0
            question = item.get("question", "")
            answer = item.get("answer", "")
            tags = item.get("tags", [])
            intent = item.get("metadata", {}).get("intent", "")

            # v1 关键词匹配 (英文/数字 split)
            for keyword in query_lower.split():
                if len(keyword) > 1:
                    if keyword in question.lower():
                        score += 3.0
                    if keyword in answer.lower():
                        score += 1.5
                    if keyword in tags:
                        score += 2.0
                    if keyword in intent:
                        score += 2.0

            # v3.3.4 中文 2-gram 匹配 (解决 "分期手续费" 等短词)
            if query_tokens:
                doc_tokens = set(self._doc_tokens[i])
                intersection = query_tokens & doc_tokens
                # 命中 token 数 / query token 数 = 召回率
                recall = len(intersection) / len(query_tokens) if query_tokens else 0
                score += recall * 8.0  # 召回率权重

            # 问题完全包含查询词
            if query_lower in question.lower():
                score += 5.0

            # 完全匹配
            if query_lower.strip() == question.strip():
                score += 10.0

            scores.append((i, score))

        # 排序
        scores.sort(key=lambda x: x[1], reverse=True)

        # 返回 top_k 结果 (score > 0)
        return [
            {**self.knowledge_base[idx], "score": round(score, 2), "retrieval_method": "keyword+2gram"}
            for idx, score in scores[:top_k] if score > 0
        ]


def create_retriever(knowledge_base: List[Dict], k: int = 5):
    """创建检索器工厂函数"""
    return SimpleRetriever(knowledge_base, k)