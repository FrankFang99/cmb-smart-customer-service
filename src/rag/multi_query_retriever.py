"""
Multi-Query Retriever (HyDE 降级版) — 业界多头检索的 0 LLM 实现
=================================================================

为什么:
- 业界 Multi-Query (LangChain / LlamaIndex): 用 LLM 把 1 个 query 生成 3-5 个变体, 各自检索, 融合
- 业界 HyDE (Hypothetical Document Embeddings, Gao et al. 2022): 用 LLM 生成假设答案, 用假设答案检索
- 本项目无 LLM, 降级方案: 关键词扩展 + 同义词替换 + 银行业务词典
- 原理一致: 把一个 query 变成多个表达, 各自检索, 融合

实现:
- QueryExpander: 1 个 query -> 3-5 个变体
  1. 原 query
  2. 同义词替换 (银行业务词典: 信用卡->银行卡->刷卡, 转账->汇款->打款 等)
  3. 关键词提取 (去停用词, 留核心名词)
  4. 子问题拆分 (按 "如何/怎么" 切分, 提取主谓宾)
- 多路检索 + RRF 融合

业界对应:
- LangChain MultiQueryRetriever: LLM 生成变体 -> 各自检索 -> 融合
- LangChain HyDERetriever: LLM 生成假设答案 -> 检索
- 本项目: 规则/词典生成变体 -> 各自检索 -> 融合 (思想一致, 工具不同)
"""
from __future__ import annotations

from typing import List, Dict, Optional, Set

from .simple_retriever import SimpleRetriever
from .hybrid_retriever import HybridRetriever, reciprocal_rank_fusion


# 银行业务同义词词典 (业界做法: 业务知识图谱 / WordNet / 行业语料库)
# 本项目 0 依赖, 手工梳理银行业高频同义词组
SYNONYM_DICT: Dict[str, List[str]] = {
    # 银行业务
    "信用卡": ["银行卡", "刷卡", "信用", "贷记卡"],
    "借记卡": ["储蓄卡", "一卡通", "招行卡", "金融IC卡"],
    "转账": ["汇款", "打款", "转钱", "转出", "划款"],
    "余额": ["余额", "还有多少钱", "账户余额", "剩多少"],
    "分期": ["分期付款", "分期还款", "账单分期", "消费分期"],
    "手续费": ["费用", "收费", "费率", "佣金"],
    "利率": ["利息", "年化", "IRR", "贷款利率"],
    "额度": ["授信", "信用额度", "可用额度", "限额"],
    "挂失": ["丢失", "丢了", "找不到", "被盗"],
    "激活": ["开卡", "启用", "开通", "卡片激活"],
    "积分": ["积分查询", "积分兑换", "信用卡积分"],
    "还款": ["还钱", "还卡", "还信用卡", "主动还款"],
    "理财": ["投资", "金融产品", "财富管理", "资产管理"],
    "贷款": ["借款", "借钱", "信用贷", "抵押贷"],
    "年化": ["年化利率", "年利率", "APR", "实际利率"],
    # 招行特色
    "95555": ["客服电话", "招行客服", "服务热线"],
    "五险一金": ["社保", "公积金", "政务服务", "民生"],
    "数字人民币": ["DCEP", "e-CNY", "央行数字货币", "数字货币"],
    "跨境": ["外汇", "境外", "海外", "国际汇款"],
    # 转人工相关
    "转人工": ["人工客服", "真人", "人工服务", "人工"],
    "投诉": ["不满", "差评", "意见反馈", "抱怨"],
}


class QueryExpander:
    """
    Query 扩展器: 1 个 query -> 多个变体

    业界对应:
    - LangChain MultiQueryRetriever: LLM 生成
    - LangChain HyDERetriever: LLM 生成假设答案
    - 本项目: 规则 + 同义词词典 + 关键词提取 (0 依赖)
    """

    def __init__(self, synonym_dict: Optional[Dict[str, List[str]]] = None):
        self.synonym_dict = synonym_dict or SYNONYM_DICT

    def expand(self, query: str) -> List[str]:
        """
        扩展 query
        返回: [原 query, 同义词版, 关键词版, ...]
        """
        variants = [query]  # 原 query 永远保留

        # 1. 同义词替换变体 (每个命中同义词生成一个变体)
        synonym_variant = self._synonym_substitute(query)
        if synonym_variant != query:
            variants.append(synonym_variant)

        # 2. 关键词提取变体 (去停用词, 留核心词)
        keyword_variant = self._extract_keywords(query)
        if keyword_variant and keyword_variant != query:
            variants.append(keyword_variant)

        # 3. 子问题拆分 (按 "如何/怎么/怎样" 切分)
        sub_questions = self._split_sub_questions(query)
        variants.extend(sub_questions)

        return list(set(variants))  # 去重

    def _synonym_substitute(self, query: str) -> str:
        """同义词替换: 找第一个命中同义词, 替换为同义词组第一个"""
        for word, syns in self.synonym_dict.items():
            if word in query:
                # 用同义词组第一个替换
                return query.replace(word, syns[0])
        return query

    def _extract_keywords(self, query: str) -> str:
        """提取核心关键词 (去停用词)"""
        STOP_WORDS = {
            "如何", "怎么", "怎样", "什么", "哪些", "哪里", "哪个", "这个", "那个",
            "我要", "我需要", "我想", "请问", "您好", "你好", "麻烦", "一下",
            "的", "了", "是", "在", "和", "与", "或", "及", "吗", "呢", "啊", "哦", "嗯", "吧", "呀",
            "我", "你", "他", "她", "它", "们", "能", "可以",
        }
        # 单字 + 2-gram 提取
        tokens = []
        for word in self.synonym_dict.keys():
            if word in query and word not in STOP_WORDS:
                tokens.append(word)
        if not tokens:
            # 退路: 取 query 里的所有 2-gram
            for i in range(len(query) - 1):
                gram = query[i:i+2]
                if gram not in STOP_WORDS and not gram.isspace():
                    tokens.append(gram)
        return " ".join(tokens[:8]) if tokens else query  # 限制 8 词

    def _split_sub_questions(self, query: str) -> List[str]:
        """拆分子问题 (按标点/连词)"""
        for sep in ["，", ",", "？", "?", "。", "  ", "  "]:
            if sep in query:
                parts = [p.strip() for p in query.split(sep) if p.strip()]
                return [p for p in parts if p != query]
        return []


class MultiQueryRetriever:
    """
    多头检索: 多个 query 变体 -> 各自检索 -> 融合

    业界对应:
    - LangChain MultiQueryRetriever (LLM 生成变体)
    - HyDE (LLM 生成假设答案)
    - 本项目: 规则/词典生成变体 (0 LLM 依赖)

    实现细节:
    - QueryExpander 生成 N 个变体 (1-5 个)
    - 每个变体用 HybridRetriever 检索
    - 所有结果用 RRF 融合
    """

    def __init__(
        self,
        knowledge_base: List[Dict],
        k: int = 5,
        use_hybrid: bool = True,
        expander: Optional[QueryExpander] = None,
    ):
        """
        Args:
            knowledge_base: 知识库
            k: top_k
            use_hybrid: True 用 Hybrid (RRF), False 用 Simple (BM25)
            expander: 自定义扩展器
        """
        self.k = k
        self.knowledge_base = knowledge_base
        self.expander = expander or QueryExpander()

        # 底层检索器
        if use_hybrid:
            self.base_retriever = HybridRetriever(knowledge_base, k=k * 2)
        else:
            self.base_retriever = SimpleRetriever(knowledge_base, k=k * 2)

    def retrieve(self, query: str, top_k: Optional[int] = None) -> List[Dict]:
        """
        多头检索
        """
        top_k = top_k or self.k

        # 1. 扩展 query
        variants = self.expander.expand(query)
        if not variants:
            variants = [query]

        # 2. 各自检索
        all_rankings: List[List[Dict]] = []
        for variant in variants:
            try:
                results = self.base_retriever.retrieve(variant, top_k=top_k * 2)
                if results:
                    all_rankings.append(results)
            except Exception:
                continue

        # 3. RRF 融合
        if not all_rankings:
            return []
        fused = reciprocal_rank_fusion(all_rankings)

        # 标记
        for doc in fused:
            doc["retrieval_method"] = "multi_query_rrf"
            doc["query_variants"] = variants

        return fused[:top_k]


def create_multi_query_retriever(knowledge_base: List[Dict], k: int = 5) -> MultiQueryRetriever:
    """工厂函数"""
    return MultiQueryRetriever(knowledge_base, k=k)
