"""
评测引擎 v6.0 — 对齐 RAGAS 工业级评测框架
==============================================

参考：RAGAS (Retrieval-Augmented Generation Assessment)
GitHub: https://github.com/explodinggradients/ragas

核心设计：
- 4 个核心指标对齐 RAGAS：faithfulness / answer_relevancy / context_precision / context_recall
- 业务侧扩展：intent_accuracy / tool_call_accuracy / compliance_risk
- 支持黄金集 + 扩展集 + 对抗集三层评测
- 评测结果输出：原始分数 + 业务转化指标（CSAT / FCR / 转人工率）

为什么从 v5 升级到 v6：
- v5 评分体系（4维度×0-3分）是招行内部标准，但与业界事实标准（RAGAS）不对齐
- v6 引入 RAGAS 4 大指标，让评测可对标 RAGAS / RAGChecker / DeepEval
- 保留业务侧扩展（意图/工具/合规），兼顾"评测通用性"和"金融业务特殊性"

作者：方逸之
更新时间：2026-06-01
"""

import json
import re
import time
import statistics
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum
from collections import defaultdict


# ============================================================
# 评分维度（对齐 RAGAS）
# ============================================================

class EvaluationMetric(str, Enum):
    """评测指标枚举 — 对齐 RAGAS + 业务扩展"""
    # RAGAS 四大核心指标
    FAITHFULNESS = "faithfulness"          # 忠实度：答案是否基于检索上下文
    ANSWER_RELEVANCY = "answer_relevancy"  # 答案相关性：答案与问题的相关程度
    CONTEXT_PRECISION = "context_precision"  # 上下文精度：检索内容的相关性
    CONTEXT_RECALL = "context_recall"      # 上下文召回率：是否检索到必要信息

    # 业务侧扩展（金融客服场景）
    INTENT_ACCURACY = "intent_accuracy"    # 意图识别准确率
    TOOL_CALL_ACCURACY = "tool_call_accuracy"  # 工具调用准确率
    COMPLIANCE_SAFE = "compliance_safe"    # 合规风控通过率


@dataclass
class MetricDefinition:
    """指标定义 + 评分标准 + 业务含义"""
    # ============ RAGAS 核心 4 项 ============
    # 1. Faithfulness（忠实度）— 衡量 AI 是否"胡编乱造"
    FAITHFULNESS = {
        "name": "Faithfulness（忠实度）",
        "definition": "生成的答案中所有事实陈述均可由检索到的上下文推导出来",
        "formula": "可被上下文支持的事实陈述数 / 事实陈述总数",
        "range": "[0, 1]，越高越好",
        "compute_method": "claim_extraction + entailment_check",
        "business_meaning": "金融场景的硬性指标——宁可拒答也不能幻觉",
        "target_threshold": 0.90,
    }
    # 2. Answer Relevancy（答案相关性）
    ANSWER_RELEVANCY = {
        "name": "Answer Relevancy（答案相关性）",
        "definition": "生成的答案与用户问题的相关程度",
        "formula": "逆向生成 N 个潜在问题，与原问题 embedding 余弦相似度均值",
        "range": "[0, 1]，越高越好",
        "compute_method": "reverse_question_generation + cosine_similarity",
        "business_meaning": "衡量 AI 是否答非所问、是否有冗余信息",
        "target_threshold": 0.85,
    }
    # 3. Context Precision（上下文精度）
    CONTEXT_PRECISION = {
        "name": "Context Precision（上下文精度）",
        "definition": "检索到的上下文中相关片段的比例",
        "formula": "Precision@k = 排名 k 之前的相关片段数 / k",
        "range": "[0, 1]，越高越好",
        "compute_method": "relevance_judgment_per_chunk",
        "business_meaning": "衡量知识库检索的精准度，间接反映 Prompt 质量",
        "target_threshold": 0.80,
    }
    # 4. Context Recall（上下文召回率）
    CONTEXT_RECALL = {
        "name": "Context Recall（上下文召回率）",
        "definition": "是否检索到了回答问题所需的所有必要信息",
        "formula": "ground_truth 中可被检索上下文支撑的陈述数 / ground_truth 总陈述数",
        "range": "[0, 1]，越高越好",
        "compute_method": "ground_truth_decomposition + attribution",
        "business_meaning": "衡量知识库覆盖度，召回不足会直接导致答非所问",
        "target_threshold": 0.85,
    }
    # ============ 业务侧扩展 3 项 ============
    INTENT_ACCURACY = {
        "name": "Intent Accuracy（意图识别准确率）",
        "definition": "AI 识别出的核心意图与标注意图完全一致的比例",
        "formula": "意图正确数 / 总样本数",
        "range": "[0, 1]，越高越好",
        "business_meaning": "客服场景的第一道门，识别错了后面全错",
        "target_threshold": 0.85,
    }
    TOOL_CALL_ACCURACY = {
        "name": "Tool Call Accuracy（工具调用准确率）",
        "definition": "工具名称 + 参数完全正确的比例",
        "formula": "工具调用正确数 / 需调用工具的样本数",
        "range": "[0, 1]，越高越好",
        "business_meaning": "Agent 任务型对话的核心能力",
        "target_threshold": 0.90,
    }
    COMPLIANCE_SAFE = {
        "name": "Compliance Safety（合规风控通过率）",
        "definition": "未触发合规风险（诈骗/洗钱/违规话术）的比例",
        "formula": "合规样本数 / 涉及合规的样本数",
        "range": "[0, 1]，越高越好",
        "business_meaning": "金融行业红线，触发即事故",
        "target_threshold": 0.98,
    }


# ============================================================
# 评测数据类
# ============================================================

@dataclass
class EvalSample:
    """单条评测样本 — 对齐 RAGAS 数据格式"""
    sample_id: str
    question: str                              # 用户问题
    answer: str = ""                           # AI 生成答案
    contexts: List[str] = field(default_factory=list)   # 检索到的上下文
    ground_truth: str = ""                     # 标准答案（用于 context_recall）
    expected_intent: str = ""                  # 标注意图
    actual_intent: str = ""                    # AI 识别意图
    expected_tools: List[str] = field(default_factory=list)  # 应调用的工具
    actual_tools: List[str] = field(default_factory=list)    # 实际调用的工具
    risk_level: str = "normal"                 # normal / sensitive / critical
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricScore:
    """单指标分数 + 诊断信息"""
    metric: str
    score: float
    details: Dict[str, Any] = field(default_factory=dict)
    threshold: float = 0.0
    passed: bool = False

    def to_dict(self):
        return {
            "metric": self.metric,
            "score": round(self.score, 4),
            "threshold": self.threshold,
            "passed": self.passed,
            **self.details,
        }


@dataclass
class SampleResult:
    """单样本评测结果 — 同时输出 RAGAS 指标 + 业务指标"""
    sample_id: str
    question: str
    metrics: Dict[str, MetricScore] = field(default_factory=dict)
    intent_match: bool = False
    tool_match: bool = False
    compliance_pass: bool = True
    elapsed_ms: float = 0.0

    @property
    def composite_score(self) -> float:
        """综合得分：RAGAS 4 项 + 业务 3 项加权平均"""
        weights = {
            EvaluationMetric.FAITHFULNESS: 0.20,
            EvaluationMetric.ANSWER_RELEVANCY: 0.15,
            EvaluationMetric.CONTEXT_PRECISION: 0.10,
            EvaluationMetric.CONTEXT_RECALL: 0.15,
            EvaluationMetric.INTENT_ACCURACY: 0.20,
            EvaluationMetric.TOOL_CALL_ACCURACY: 0.10,
            EvaluationMetric.COMPLIANCE_SAFE: 0.10,
        }
        total = 0.0
        for metric_name, weight in weights.items():
            m = self.metrics.get(metric_name.value)
            if m:
                total += m.score * weight
        return round(total, 4)

    @property
    def grade(self) -> str:
        """评级"""
        s = self.composite_score
        if s >= 0.90:
            return "S"
        elif s >= 0.80:
            return "A"
        elif s >= 0.70:
            return "B"
        elif s >= 0.60:
            return "C"
        return "D"


@dataclass
class DatasetReport:
    """数据集级评测报告"""
    dataset_name: str
    total_samples: int
    metric_aggregates: Dict[str, Dict[str, float]] = field(default_factory=dict)
    sample_results: List[SampleResult] = field(default_factory=list)
    business_kpis: Dict[str, float] = field(default_factory=dict)
    badcases: List[SampleResult] = field(default_factory=list)
    elapsed_seconds: float = 0.0

    def to_dict(self):
        return {
            "dataset_name": self.dataset_name,
            "total_samples": self.total_samples,
            "metric_aggregates": self.metric_aggregates,
            "business_kpis": self.business_kpis,
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "badcase_count": len(self.badcases),
        }


# ============================================================
# RAGAS 风格指标计算器
# ============================================================

class RAGASScorer:
    """
    RAGAS 4 大指标计算器
    注：生产环境推荐直接调用 ragas 库；这里给出纯 Python 简化版（基于 LLM 调用）
    """

    def __init__(self, llm_callable=None):
        """
        Args:
            llm_callable: 一个可调用的 LLM 接口，签名 llm(prompt: str) -> str
                          传 None 时使用基于规则的 fallback（仅用于 demo）
        """
        self.llm = llm_callable

    def faithfulness(self, question: str, answer: str, contexts: List[str]) -> MetricScore:
        """
        Faithfulness（忠实度）
        = 可被上下文支持的事实陈述数 / 事实陈述总数

        步骤：
        1. 将 answer 拆分为多个事实陈述（claims）
        2. 对每个 claim，用 contexts 验证是否可推导
        3. 得分 = supported_claims / total_claims
        """
        if not answer or not contexts:
            return MetricScore(
                metric=EvaluationMetric.FAITHFULNESS.value,
                score=0.0,
                details={"reason": "empty_answer_or_context"},
                threshold=0.90,
                passed=False,
            )

        # Step 1: 拆分事实陈述（简化版：按句号切分；生产用 LLM）
        claims = [c.strip() for c in re.split(r'[。！？\n]', answer) if c.strip()]
        if not claims:
            return MetricScore(
                metric=EvaluationMetric.FAITHFULNESS.value,
                score=1.0,
                details={"reason": "no_claims"},
                threshold=0.90,
                passed=True,
            )

        # Step 2: 验证每个 claim（生产用 LLM-as-judge）
        context_text = "\n".join(contexts)
        if self.llm:
            supported = self._llm_verify_claims(claims, context_text)
        else:
            supported = self._rule_based_verify(claims, context_text)

        score = len(supported) / len(claims)
        return MetricScore(
            metric=EvaluationMetric.FAITHFULNESS.value,
            score=score,
            details={
                "total_claims": len(claims),
                "supported_claims": len(supported),
                "unsupported_claims": [c for c in claims if c not in supported],
            },
            threshold=0.90,
            passed=score >= 0.90,
        )

    def answer_relevancy(self, question: str, answer: str, n: int = 3) -> MetricScore:
        """
        Answer Relevancy（答案相关性）
        = 逆向生成 n 个潜在问题，与原问题 embedding 余弦相似度均值

        业务意义：答案不完整或含冗余信息时扣分
        """
        if not answer or not question:
            return MetricScore(
                metric=EvaluationMetric.ANSWER_RELEVANCY.value,
                score=0.0,
                details={"reason": "empty_input"},
                threshold=0.85,
                passed=False,
            )

        # 简化版：用 LLM 逆向生成问题，再算 embedding 相似度
        if self.llm:
            generated_questions = self._llm_generate_questions(answer, n)
            similarities = self._compute_similarities(question, generated_questions)
            score = statistics.mean(similarities) if similarities else 0.0
        else:
            # Fallback: 关键词重合度
            q_words = set(question)
            a_words = set(answer)
            overlap = len(q_words & a_words)
            score = overlap / max(len(q_words), 1) if q_words else 0.0

        return MetricScore(
            metric=EvaluationMetric.ANSWER_RELEVANCY.value,
            score=score,
            details={"n_candidate_questions": n},
            threshold=0.85,
            passed=score >= 0.85,
        )

    def context_precision(self, question: str, contexts: List[str]) -> MetricScore:
        """
        Context Precision（上下文精度）
        = rank k 之前的相关片段数 / k

        业务意义：检索器是否精准——如果召回了大量无关内容会拉低此分
        """
        if not contexts:
            return MetricScore(
                metric=EvaluationMetric.CONTEXT_PRECISION.value,
                score=0.0,
                details={"reason": "no_context"},
                threshold=0.80,
                passed=False,
            )

        # 对每个 context 片段判断是否与问题相关
        relevance_flags = []
        for ctx in contexts:
            if self.llm:
                relevant = self._llm_judge_relevance(question, ctx)
            else:
                relevant = self._rule_based_relevance(question, ctx)
            relevance_flags.append(1 if relevant else 0)

        # Precision@k = sum(flags[:k]) / k
        k = len(contexts)
        relevant_at_k = sum(relevance_flags)
        score = relevant_at_k / k

        return MetricScore(
            metric=EvaluationMetric.CONTEXT_PRECISION.value,
            score=score,
            details={"k": k, "relevant_chunks": relevant_at_k},
            threshold=0.80,
            passed=score >= 0.80,
        )

    def context_recall(
        self,
        question: str,
        ground_truth: str,
        contexts: List[str]
    ) -> MetricScore:
        """
        Context Recall（上下文召回率）
        = ground_truth 中可被 contexts 支撑的陈述数 / ground_truth 总陈述数

        业务意义：知识库覆盖度——如果必要信息没检索到，答案一定不对
        """
        if not ground_truth:
            return MetricScore(
                metric=EvaluationMetric.CONTEXT_RECALL.value,
                score=1.0,
                details={"reason": "no_ground_truth"},
                threshold=0.85,
                passed=True,
            )
        if not contexts:
            return MetricScore(
                metric=EvaluationMetric.CONTEXT_RECALL.value,
                score=0.0,
                details={"reason": "no_context"},
                threshold=0.85,
                passed=False,
            )

        # Step 1: 拆分 ground_truth 为陈述
        gt_claims = [c.strip() for c in re.split(r'[。！？\n]', ground_truth) if c.strip()]
        if not gt_claims:
            return MetricScore(
                metric=EvaluationMetric.CONTEXT_RECALL.value,
                score=1.0,
                details={"reason": "no_claims"},
                threshold=0.85,
                passed=True,
            )

        # Step 2: 对每个 claim 检查是否被 contexts 覆盖
        context_text = "\n".join(contexts)
        if self.llm:
            attributed = self._llm_verify_claims(gt_claims, context_text)
        else:
            attributed = self._rule_based_verify(gt_claims, context_text)

        score = len(attributed) / len(gt_claims)
        return MetricScore(
            metric=EvaluationMetric.CONTEXT_RECALL.value,
            score=score,
            details={
                "total_gt_claims": len(gt_claims),
                "attributed_claims": len(attributed),
            },
            threshold=0.85,
            passed=score >= 0.85,
        )

    # ============ 内部 LLM 调用方法 ============
    def _llm_verify_claims(self, claims: List[str], context: str) -> List[str]:
        """LLM-as-judge：验证每个 claim 是否可由 context 推出"""
        prompt = f"""判断以下陈述是否能从给定上下文中直接推出。逐行回答 Yes/No。

上下文：{context}

陈述：
{chr(10).join(f'{i+1}. {c}' for i, c in enumerate(claims))}

格式：每行一个 Yes/No"""
        response = self.llm(prompt) if self.llm else ""
        lines = response.strip().split("\n")
        supported = []
        for claim, line in zip(claims, lines):
            if "Yes" in line or "yes" in line:
                supported.append(claim)
        return supported

    def _llm_generate_questions(self, answer: str, n: int) -> List[str]:
        """LLM 逆向生成问题"""
        prompt = f"基于以下答案，生成 {n} 个可能的问题：\n{answer}"
        response = self.llm(prompt) if self.llm else ""
        return [q.strip() for q in response.split("\n") if q.strip()][:n]

    def _llm_judge_relevance(self, question: str, context: str) -> bool:
        """LLM 判断 context 与 question 是否相关"""
        prompt = f"问题：{question}\n片段：{context}\n这个片段对回答问题是否相关？Yes/No"
        response = self.llm(prompt) if self.llm else ""
        return "Yes" in response or "yes" in response

    def _compute_similarities(self, q1: str, candidates: List[str]) -> List[float]:
        """计算 embedding 相似度（生产用 sentence-transformers）"""
        # 简化版：返回 0.5 占位
        return [0.5] * len(candidates)

    def _rule_based_verify(self, claims: List[str], context: str) -> List[str]:
        """规则 fallback：关键词匹配"""
        supported = []
        context_words = set(context)
        for claim in claims:
            claim_words = set(claim)
            overlap = len(claim_words & context_words)
            if overlap >= max(len(claim_words) * 0.3, 1):
                supported.append(claim)
        return supported

    def _rule_based_relevance(self, question: str, context: str) -> bool:
        """规则 fallback：关键词重合度"""
        q_words = set(question) & set("的了吗呢啊我你他她它")
        common = set(question) & set(context)
        return len(common) > 0


# ============================================================
# 业务侧指标计算器
# ============================================================

class BusinessScorer:
    """业务侧扩展指标：意图/工具/合规"""

    @staticmethod
    def intent_accuracy(expected: str, actual: str) -> MetricScore:
        """意图识别准确率（核心 + 次要 全部匹配才算对）"""
        match = (expected == actual)
        return MetricScore(
            metric=EvaluationMetric.INTENT_ACCURACY.value,
            score=1.0 if match else 0.0,
            details={"expected": expected, "actual": actual},
            threshold=0.85,
            passed=match,
        )

    @staticmethod
    def tool_call_accuracy(expected: List[str], actual: List[str]) -> MetricScore:
        """工具调用准确率"""
        if not expected:
            return MetricScore(
                metric=EvaluationMetric.TOOL_CALL_ACCURACY.value,
                score=1.0,
                details={"reason": "no_tool_required"},
                threshold=0.90,
                passed=True,
            )
        matched = sum(1 for t in expected if t in actual)
        score = matched / len(expected)
        return MetricScore(
            metric=EvaluationMetric.TOOL_CALL_ACCURACY.value,
            score=score,
            details={"expected": expected, "actual": actual, "matched": matched},
            threshold=0.90,
            passed=score >= 0.90,
        )

    @staticmethod
    def compliance_check(
        answer: str,
        risk_level: str,
        forbidden_patterns: Optional[List[str]] = None,
    ) -> MetricScore:
        """
        合规风控检查
        - risk_level=critical：必须包含"建议联系人工"等转人工话术
        - 默认检查：是否含明文密码、身份证号、手机号等敏感信息
        """
        if forbidden_patterns is None:
            forbidden_patterns = [
                r'\d{17}[\dXx]',  # 身份证
                r'\d{11}',         # 手机号
                r'密码是\s*\S+',   # 明文密码
            ]

        violations = []
        for pattern in forbidden_patterns:
            if re.search(pattern, answer):
                violations.append(pattern)

        # critical 场景必须转人工
        if risk_level == "critical":
            transfer_keywords = ["人工", "客服", "95555", "客户经理"]
            if not any(kw in answer for kw in transfer_keywords):
                violations.append("missing_transfer_suggestion")

        passed = len(violations) == 0
        return MetricScore(
            metric=EvaluationMetric.COMPLIANCE_SAFE.value,
            score=1.0 if passed else 0.0,
            details={"risk_level": risk_level, "violations": violations},
            threshold=0.98,
            passed=passed,
        )


# ============================================================
# 评测运行器 v6
# ============================================================

class EvalRunnerV6:
    """
    评测引擎 v6 — 对齐 RAGAS 工业级框架
    """

    def __init__(self, llm_callable=None):
        self.ragas_scorer = RAGASScorer(llm_callable=llm_callable)
        self.business_scorer = BusinessScorer()

    def evaluate_sample(self, sample: EvalSample) -> SampleResult:
        """评测单条样本"""
        t0 = time.time()
        result = SampleResult(sample_id=sample.sample_id, question=sample.question)

        # ============ RAGAS 4 大指标 ============
        result.metrics[EvaluationMetric.FAITHFULNESS.value] = self.ragas_scorer.faithfulness(
            sample.question, sample.answer, sample.contexts
        )
        result.metrics[EvaluationMetric.ANSWER_RELEVANCY.value] = self.ragas_scorer.answer_relevancy(
            sample.question, sample.answer
        )
        result.metrics[EvaluationMetric.CONTEXT_PRECISION.value] = self.ragas_scorer.context_precision(
            sample.question, sample.contexts
        )
        result.metrics[EvaluationMetric.CONTEXT_RECALL.value] = self.ragas_scorer.context_recall(
            sample.question, sample.ground_truth, sample.contexts
        )

        # ============ 业务侧 3 项 ============
        result.metrics[EvaluationMetric.INTENT_ACCURACY.value] = self.business_scorer.intent_accuracy(
            sample.expected_intent, sample.actual_intent
        )
        result.metrics[EvaluationMetric.TOOL_CALL_ACCURACY.value] = self.business_scorer.tool_call_accuracy(
            sample.expected_tools, sample.actual_tools
        )
        result.metrics[EvaluationMetric.COMPLIANCE_SAFE.value] = self.business_scorer.compliance_check(
            sample.answer, sample.risk_level
        )

        # 业务标签
        result.intent_match = result.metrics[EvaluationMetric.INTENT_ACCURACY.value].score >= 1.0
        result.tool_match = result.metrics[EvaluationMetric.TOOL_CALL_ACCURACY.value].score >= 1.0
        result.compliance_pass = result.metrics[EvaluationMetric.COMPLIANCE_SAFE.value].score >= 1.0
        result.elapsed_ms = (time.time() - t0) * 1000

        return result

    def evaluate_dataset(self, samples: List[EvalSample], dataset_name: str = "default") -> DatasetReport:
        """评测整个数据集"""
        t0 = time.time()
        report = DatasetReport(
            dataset_name=dataset_name,
            total_samples=len(samples),
        )

        # 跑每条样本
        for sample in samples:
            result = self.evaluate_sample(sample)
            report.sample_results.append(result)

        # 聚合指标
        report.metric_aggregates = self._aggregate_metrics(report.sample_results)
        # 计算业务 KPI
        report.business_kpis = self._compute_business_kpis(report.sample_results)
        # 提取 badcase（综合分 < 0.6 或任一 RAGAS 指标 < 阈值）
        report.badcases = [
            r for r in report.sample_results
            if r.composite_score < 0.6 or any(
                m.passed is False for m in r.metrics.values()
            )
        ]
        report.elapsed_seconds = time.time() - t0
        return report

    def _aggregate_metrics(self, results: List[SampleResult]) -> Dict[str, Dict[str, float]]:
        """聚合每个指标的均值、中位数、P95"""
        aggregates = {}
        for metric in EvaluationMetric:
            scores = [r.metrics[metric.value].score for r in results if metric.value in r.metrics]
            if not scores:
                continue
            scores_sorted = sorted(scores)
            p95_idx = int(len(scores_sorted) * 0.95)
            p95 = scores_sorted[min(p95_idx, len(scores_sorted) - 1)]
            aggregates[metric.value] = {
                "mean": round(statistics.mean(scores), 4),
                "median": round(statistics.median(scores), 4),
                "stdev": round(statistics.stdev(scores), 4) if len(scores) > 1 else 0.0,
                "p95": round(p95, 4),
                "min": round(min(scores), 4),
                "max": round(max(scores), 4),
                "pass_rate": round(
                    sum(1 for r in results if r.metrics[metric.value].passed) / len(results), 4
                ) if results else 0.0,
            }
        return aggregates

    def _compute_business_kpis(self, results: List[SampleResult]) -> Dict[str, float]:
        """
        业务 KPI 计算（对齐业界四象限）
        - FCR (First Contact Resolution)
        - 转人工率
        - CSAT 预估（基于综合得分）
        - P95 响应时长
        """
        if not results:
            return {}

        n = len(results)
        # FCR: 综合得分 >= 0.8 视为一次解决
        fcr = sum(1 for r in results if r.composite_score >= 0.8) / n
        # 转人工率：合规未通过或综合分 < 0.6（需人工介入）
        transfer_rate = sum(
            1 for r in results
            if not r.compliance_pass or r.composite_score < 0.6
        ) / n
        # CSAT 预估：综合得分 -> 1-5 分（线性映射）
        csat_scores = [1 + r.composite_score * 4 for r in results]
        csat_avg = statistics.mean(csat_scores)
        # P95 响应时长
        elapsed_sorted = sorted([r.elapsed_ms for r in results])
        p95_idx = int(n * 0.95)
        p95_latency = elapsed_sorted[min(p95_idx, n - 1)]

        return {
            "FCR": round(fcr, 4),
            "transfer_rate": round(transfer_rate, 4),
            "CSAT_estimated": round(csat_avg, 2),
            "P95_latency_ms": round(p95_latency, 2),
            "S_grade_rate": round(sum(1 for r in results if r.grade == "S") / n, 4),
        }


# ============================================================
# CLI 入口
# ============================================================

def main():
    import sys
    print("=" * 70)
    print("评测引擎 v6.0 — 对齐 RAGAS 工业级框架")
    print("=" * 70)
    print()
    print("支持的指标（7 项）：")
    print()
    print("[RAGAS 4 大核心指标]")
    print(f"  1. {MetricDefinition.FAITHFULNESS['name']:<30} 阈值 ≥ {MetricDefinition.FAITHFULNESS['target_threshold']}")
    print(f"  2. {MetricDefinition.ANSWER_RELEVANCY['name']:<30} 阈值 ≥ {MetricDefinition.ANSWER_RELEVANCY['target_threshold']}")
    print(f"  3. {MetricDefinition.CONTEXT_PRECISION['name']:<30} 阈值 ≥ {MetricDefinition.CONTEXT_PRECISION['target_threshold']}")
    print(f"  4. {MetricDefinition.CONTEXT_RECALL['name']:<30} 阈值 ≥ {MetricDefinition.CONTEXT_RECALL['target_threshold']}")
    print()
    print("[业务侧扩展 3 项]")
    print(f"  5. {MetricDefinition.INTENT_ACCURACY['name']:<30} 阈值 ≥ {MetricDefinition.INTENT_ACCURACY['target_threshold']}")
    print(f"  6. {MetricDefinition.TOOL_CALL_ACCURACY['name']:<30} 阈值 ≥ {MetricDefinition.TOOL_CALL_ACCURACY['target_threshold']}")
    print(f"  7. {MetricDefinition.COMPLIANCE_SAFE['name']:<30} 阈值 ≥ {MetricDefinition.COMPLIANCE_SAFE['target_threshold']}")
    print()
    print("=" * 70)
    print()
    print("使用示例：")
    print("  from src.eval.eval_runner_v6 import EvalRunnerV6, EvalSample")
    print("  runner = EvalRunnerV6(llm_callable=your_llm_fn)")
    print("  report = runner.evaluate_dataset(samples, dataset_name='v6_test')")
    print("  print(report.to_dict())")
    print()


if __name__ == "__main__":
    main()
