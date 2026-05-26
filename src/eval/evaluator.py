"""
评测模块
包含评测集管理、评测指标计算、Badcase 管理
"""
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json


@dataclass
class EvaluationSample:
    """评测样本"""
    id: str
    query: str
    expected_intent: str
    category: str
    layer: str  # high_freq / boundary / compliance
    expected_risk_disclosure: bool = False
    expected_human_transfer: bool = False
    expected_answer_keywords: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)


@dataclass
class EvaluationResult:
    """评测结果"""
    sample_id: str
    query: str
    predicted_intent: str
    expected_intent: str
    intent_correct: bool
    intent_confidence: float
    predicted_risk_disclosure: bool
    expected_risk_disclosure: bool
    risk_disclosure_correct: bool
    predicted_human_transfer: bool
    expected_human_transfer: bool
    human_transfer_correct: bool
    answer_quality: float  # 0-1
    keyword_coverage: float  # 0-1
    overall_score: float  # 0-1
    error_type: Optional[str] = None
    feedback: Optional[str] = None


@dataclass
class EvaluationMetrics:
    """评测指标汇总"""
    # 意图识别
    intent_accuracy: float
    intent_coverage: float

    # 回答质量
    answer_accuracy: float
    answer_completeness: float
    answer_relevance: float

    # 知识库
    kb_match_rate: float
    retrieval_recall: float

    # 合规安全
    risk_disclosure_rate: float
    human_transfer_accuracy: float
    script_compliance_rate: float

    # 用户体验
    csat_score: float
    first_resolution_rate: float
    repeat_query_rate: float

    # 综合得分
    overall_score: float


class EvaluationDataset:
    """
    评测数据集管理
    - 加载评测集
    - 种子问题扩展
    - Badcase 管理
    """

    def __init__(self):
        self.samples: List[EvaluationSample] = []
        self.bad_cases: List[Dict] = []

    def load_from_json(self, file_path: str):
        """从 JSON 文件加载评测集"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for item in data:
            self.samples.append(EvaluationSample(
                id=item["id"],
                query=item["query"],
                expected_intent=item["expected_intent"],
                category=item.get("category", "unknown"),
                layer=item.get("layer", "high_freq"),
                expected_risk_disclosure=item.get("expected_risk_disclosure", False),
                expected_human_transfer=item.get("expected_human_transfer", False),
                expected_answer_keywords=item.get("expected_answer_keywords", []),
                metadata=item.get("metadata", {})
            ))

    def load_from_dict(self, data: List[Dict]):
        """从字典列表加载评测集"""
        for item in data:
            self.samples.append(EvaluationSample(
                id=item["id"],
                query=item["query"],
                expected_intent=item["expected_intent"],
                category=item.get("category", "unknown"),
                layer=item.get("layer", "high_freq"),
                expected_risk_disclosure=item.get("expected_risk_disclosure", False),
                expected_human_transfer=item.get("expected_human_transfer", False),
                expected_answer_keywords=item.get("expected_answer_keywords", []),
                metadata=item.get("metadata", {})
            ))

    def add_sample(self, sample: EvaluationSample):
        """添加单个样本"""
        self.samples.append(sample)

    def add_bad_case(self, case: Dict):
        """添加 Badcase"""
        case["created_at"] = datetime.now().isoformat()
        self.bad_cases.append(case)

    def get_by_intent(self, intent: str) -> List[EvaluationSample]:
        """按意图筛选样本"""
        return [s for s in self.samples if s.expected_intent == intent]

    def get_by_layer(self, layer: str) -> List[EvaluationSample]:
        """按层级筛选样本"""
        return [s for s in self.samples if s.layer == layer]

    def get_by_category(self, category: str) -> List[EvaluationSample]:
        """按分类筛选样本"""
        return [s for s in self.samples if s.category == category]

    def generate_seed_expansions(self, seed_queries: List[str], n_variations: int = 5) -> List[str]:
        """
        种子问题扩展
        使用同义词、句式变换等方式生成相似问题
        """
        expansions = []

        for query in seed_queries:
            # 简单规则扩展
            variations = [
                query,  # 原句
                f"请问{query}",  # 加请问
                f"{query}吗",  # 加吗
                f"我想{query}",  # 加我想
                f"怎么{query}",  # 改成怎么
                query.replace("？", "").replace("?", ""),  # 去问号
            ]
            expansions.extend(variations[:n_variations])

        return expansions

    def get_statistics(self) -> Dict:
        """获取评测集统计信息"""
        total = len(self.samples)
        by_layer = {}
        by_category = {}
        by_intent = {}

        for sample in self.samples:
            by_layer[sample.layer] = by_layer.get(sample.layer, 0) + 1
            by_category[sample.category] = by_category.get(sample.category, 0) + 1
            by_intent[sample.expected_intent] = by_intent.get(sample.expected_intent, 0) + 1

        return {
            "total_samples": total,
            "by_layer": by_layer,
            "by_category": by_category,
            "by_intent": by_intent,
            "unique_intents": len(by_intent),
            "unique_categories": len(by_category)
        }


class Evaluator:
    """
    评测器
    - 计算意图准确率
    - 计算回答质量
    - 生成评测报告
    """

    def __init__(self):
        self.results: List[EvaluationResult] = []

    def evaluate_response(
        self,
        sample: EvaluationSample,
        response: Dict
    ) -> EvaluationResult:
        """
        评测单条回复

        Args:
            sample: 评测样本
            response: Agent 返回的响应

        Returns:
            EvaluationResult: 评测结果
        """
        predicted_intent = response.get("intent", "unknown")
        predicted_risk = response.get("risk_disclosure", False)
        predicted_human = response.get("human_transfer", False)
        answer = response.get("answer", "")
        confidence = response.get("confidence", 0.5)

        # 意图准确率
        intent_correct = predicted_intent == sample.expected_intent

        # 风险提示准确率
        risk_disclosure_correct = predicted_risk == sample.expected_risk_disclosure

        # 转人工准确率
        human_transfer_correct = predicted_human == sample.expected_human_transfer

        # 关键词覆盖率
        keyword_coverage = self._calculate_keyword_coverage(
            sample.expected_answer_keywords,
            answer
        )

        # 回答质量（综合评估）
        answer_quality = self._calculate_answer_quality(
            sample.expected_intent,
            answer
        )

        # 综合得分
        overall_score = self._calculate_overall_score(
            intent_correct,
            risk_disclosure_correct,
            human_transfer_correct,
            answer_quality,
            keyword_coverage
        )

        # 错误类型
        error_type = self._get_error_type(
            intent_correct,
            risk_disclosure_correct,
            human_transfer_correct,
            keyword_coverage
        )

        return EvaluationResult(
            sample_id=sample.id,
            query=sample.query,
            predicted_intent=predicted_intent,
            expected_intent=sample.expected_intent,
            intent_correct=intent_correct,
            intent_confidence=confidence,
            predicted_risk_disclosure=predicted_risk,
            expected_risk_disclosure=sample.expected_risk_disclosure,
            risk_disclosure_correct=risk_disclosure_correct,
            predicted_human_transfer=predicted_human,
            expected_human_transfer=sample.expected_human_transfer,
            human_transfer_correct=human_transfer_correct,
            answer_quality=answer_quality,
            keyword_coverage=keyword_coverage,
            overall_score=overall_score,
            error_type=error_type
        )

    def _calculate_keyword_coverage(
        self,
        expected_keywords: List[str],
        answer: str
    ) -> float:
        """计算关键词覆盖率"""
        if not expected_keywords:
            return 1.0

        answer_lower = answer.lower()
        matched = sum(1 for kw in expected_keywords if kw.lower() in answer_lower)
        return matched / len(expected_keywords)

    def _calculate_answer_quality(self, intent: str, answer: str) -> float:
        """计算回答质量"""
        if not answer:
            return 0.0

        # 基础质量评估
        quality = 0.5

        # 检查回答长度
        if len(answer) < 10:
            quality -= 0.2
        elif len(answer) > 50:
            quality += 0.1

        # 检查是否有实质内容
        if any(marker in answer for marker in ["抱歉", "感谢", "请问"]):
            quality += 0.1

        # 检查是否提到具体信息
        if any(marker in answer for marker in ["手机银行", "95555", "网点", "APP"]):
            quality += 0.1

        return min(1.0, max(0.0, quality))

    def _calculate_overall_score(
        self,
        intent_correct: bool,
        risk_correct: bool,
        human_correct: bool,
        answer_quality: float,
        keyword_coverage: float
    ) -> float:
        """计算综合得分"""
        # 权重配置
        intent_weight = 0.30
        risk_weight = 0.15
        human_weight = 0.15
        answer_weight = 0.25
        keyword_weight = 0.15

        intent_score = 1.0 if intent_correct else 0.0
        risk_score = 1.0 if risk_correct else 0.0
        human_score = 1.0 if human_correct else 0.0

        return (
            intent_score * intent_weight +
            risk_score * risk_weight +
            human_score * human_weight +
            answer_quality * answer_weight +
            keyword_coverage * keyword_weight
        )

    def _get_error_type(
        self,
        intent_correct: bool,
        risk_correct: bool,
        human_correct: bool,
        keyword_coverage: float
    ) -> Optional[str]:
        """判断错误类型"""
        if intent_correct and risk_correct and human_correct and keyword_coverage >= 0.8:
            return None

        if not intent_correct:
            return "intent_error"

        errors = []
        if not risk_correct:
            errors.append("risk_disclosure_error")
        if not human_correct:
            errors.append("human_transfer_error")
        if keyword_coverage < 0.5:
            errors.append("answer_quality_error")

        return "_".join(errors) if errors else "partial_error"

    def evaluate_batch(
        self,
        dataset: EvaluationDataset,
        agent,
        session_prefix: str = "eval"
    ) -> List[EvaluationResult]:
        """批量评测"""
        results = []

        for sample in dataset.samples:
            response = agent.chat(sample.query, session_id=f"{session_prefix}_{sample.id}")
            result = self.evaluate_response(sample, response)
            results.append(result)

        self.results = results
        return results

    def calculate_metrics(self) -> EvaluationMetrics:
        """计算评测指标汇总"""
        if not self.results:
            return None

        total = len(self.results)

        # 意图识别
        intent_correct = sum(1 for r in self.results if r.intent_correct)
        intent_accuracy = intent_correct / total if total > 0 else 0

        # 回答质量
        avg_answer_quality = sum(r.answer_quality for r in self.results) / total
        avg_keyword_coverage = sum(r.keyword_coverage for r in self.results) / total

        # 合规安全
        risk_correct = sum(1 for r in self.results if r.risk_disclosure_correct)
        human_correct = sum(1 for r in self.results if r.human_transfer_correct)
        risk_rate = risk_correct / total if total > 0 else 0
        human_rate = human_correct / total if total > 0 else 0

        # 综合得分
        avg_overall = sum(r.overall_score for r in self.results) / total

        return EvaluationMetrics(
            intent_accuracy=intent_accuracy,
            intent_coverage=0.85,  # 假设覆盖率
            answer_accuracy=avg_keyword_coverage,
            answer_completeness=avg_answer_quality,
            answer_relevance=avg_answer_quality,
            kb_match_rate=0.90,  # 假设值
            retrieval_recall=0.85,  # 假设值
            risk_disclosure_rate=risk_rate,
            human_transfer_accuracy=human_rate,
            script_compliance_rate=0.95,  # 假设值
            csat_score=0.85,  # 假设值
            first_resolution_rate=0.80,  # 假设值
            repeat_query_rate=0.05,  # 假设值
            overall_score=avg_overall
        )

    def generate_report(self) -> Dict:
        """生成评测报告"""
        if not self.results:
            return {"error": "No evaluation results"}

        total = len(self.results)
        metrics = self.calculate_metrics()

        # 按错误类型分组
        error_types = {}
        for r in self.results:
            if r.error_type:
                error_types[r.error_type] = error_types.get(r.error_type, 0) + 1

        # 按意图统计
        intent_stats = {}
        for r in self.results:
            if r.expected_intent not in intent_stats:
                intent_stats[r.expected_intent] = {"correct": 0, "total": 0}
            intent_stats[r.expected_intent]["total"] += 1
            if r.intent_correct:
                intent_stats[r.expected_intent]["correct"] += 1

        # 按层级统计
        layer_stats = {}
        for r in self.results:
            sample = next((s for s in self.results if s.sample_id == r.sample_id), None)
            if sample:
                layer = sample.layer
                if layer not in layer_stats:
                    layer_stats[layer] = {"correct": 0, "total": 0}
                layer_stats[layer]["total"] += 1
                if r.intent_correct:
                    layer_stats[layer]["correct"] += 1

        # Bad cases
        bad_cases = [
            {
                "sample_id": r.sample_id,
                "query": r.query,
                "predicted_intent": r.predicted_intent,
                "expected_intent": r.expected_intent,
                "error_type": r.error_type,
                "overall_score": r.overall_score
            }
            for r in self.results if r.overall_score < 0.7
        ]

        return {
            "report_date": datetime.now().isoformat(),
            "summary": {
                "total_samples": total,
                "intent_accuracy": metrics.intent_accuracy,
                "risk_disclosure_rate": metrics.risk_disclosure_rate,
                "human_transfer_accuracy": metrics.human_transfer_accuracy,
                "overall_score": metrics.overall_score
            },
            "error_distribution": error_types,
            "intent_stats": {
                intent: {
                    "accuracy": stats["correct"] / stats["total"] if stats["total"] > 0 else 0,
                    "count": stats["total"]
                }
                for intent, stats in intent_stats.items()
            },
            "layer_stats": {
                layer: {
                    "accuracy": stats["correct"] / stats["total"] if stats["total"] > 0 else 0,
                    "count": stats["total"]
                }
                for layer, stats in layer_stats.items()
            },
            "bad_cases": bad_cases,
            "recommendations": self._generate_recommendations(error_types)
        }

    def _generate_recommendations(self, error_types: Dict) -> List[str]:
        """生成优化建议"""
        recommendations = []

        if error_types.get("intent_error", 0) > 5:
            recommendations.append("意图识别准确率偏低，建议扩充训练数据或优化意图分类模型")

        if error_types.get("risk_disclosure_error", 0) > 3:
            recommendations.append("风险提示缺失较多，建议检查涉及投资、贷款业务的知识库条目")

        if error_types.get("human_transfer_error", 0) > 3:
            recommendations.append("转人工判定有误，建议优化边界场景的处理逻辑")

        if error_types.get("answer_quality_error", 0) > 5:
            recommendations.append("回答质量偏低，建议丰富知识库内容或优化生成策略")

        if not recommendations:
            recommendations.append("系统整体表现良好，建议持续监控并收集 Badcase 进行迭代优化")

        return recommendations


# ===== 内置评测集（精简版）=====
DEFAULT_EVAL_DATASET = [
    {"id": "e001", "query": "查一下我的账户余额", "expected_intent": "account_balance",
     "category": "account", "layer": "high_freq", "expected_risk_disclosure": False,
     "expected_human_transfer": False, "expected_answer_keywords": ["余额", "查询方式"]},
    {"id": "e002", "query": "我还有多少钱", "expected_intent": "account_balance",
     "category": "account", "layer": "boundary", "expected_risk_disclosure": False,
     "expected_human_transfer": False, "expected_answer_keywords": ["余额"]},
    {"id": "e009", "query": "我的信用卡账单是多少", "expected_intent": "bill_query",
     "category": "credit_card", "layer": "high_freq", "expected_risk_disclosure": False,
     "expected_human_transfer": False, "expected_answer_keywords": ["账单", "还款"]},
    {"id": "e014", "query": "信用卡还款方式有哪些", "expected_intent": "repayment_method",
     "category": "credit_card", "layer": "high_freq", "expected_risk_disclosure": False,
     "expected_human_transfer": False, "expected_answer_keywords": ["还款方式", "自动还款"]},
    {"id": "e017", "query": "信用卡丢了怎么办", "expected_intent": "card_loss",
     "category": "credit_card", "layer": "high_freq", "expected_risk_disclosure": False,
     "expected_human_transfer": False, "expected_answer_keywords": ["挂失", "补卡"]},
    {"id": "e022", "query": "现在有什么理财产品", "expected_intent": "product_query",
     "category": "investment", "layer": "high_freq", "expected_risk_disclosure": True,
     "expected_human_transfer": False, "expected_answer_keywords": ["理财", "风险"]},
    {"id": "e025", "query": "买基金有什么风险", "expected_intent": "fund_risk",
     "category": "investment", "layer": "high_freq", "expected_risk_disclosure": True,
     "expected_human_transfer": False, "expected_answer_keywords": ["基金", "风险", "亏损"]},
    {"id": "e030", "query": "我想贷款", "expected_intent": "loan_inquiry",
     "category": "loan", "layer": "high_freq", "expected_risk_disclosure": True,
     "expected_human_transfer": False, "expected_answer_keywords": ["贷款", "利率"]},
    {"id": "e035", "query": "如何转账", "expected_intent": "transfer_guide",
     "category": "payment", "layer": "high_freq", "expected_risk_disclosure": False,
     "expected_human_transfer": False, "expected_answer_keywords": ["转账", "操作"]},
    {"id": "e040", "query": "最近的网点在哪", "expected_intent": "branch_query",
     "category": "life_service", "layer": "high_freq", "expected_risk_disclosure": False,
     "expected_human_transfer": False, "expected_answer_keywords": ["网点", "地址"]},
    {"id": "e045", "query": "你好", "expected_intent": "greeting",
     "category": "service", "layer": "high_freq", "expected_risk_disclosure": False,
     "expected_human_transfer": False, "expected_answer_keywords": ["您好", "欢迎"]},
    {"id": "e049", "query": "我要投诉", "expected_intent": "complaint",
     "category": "service", "layer": "high_freq", "expected_risk_disclosure": False,
     "expected_human_transfer": True, "expected_answer_keywords": ["投诉", "反馈"]},
    {"id": "e051", "query": "转人工", "expected_intent": "human_service",
     "category": "service", "layer": "high_freq", "expected_risk_disclosure": False,
     "expected_human_transfer": True, "expected_answer_keywords": ["人工", "转接"]},
    {"id": "e054", "query": "更多产品推荐", "expected_intent": "product_more",
     "category": "investment", "layer": "boundary", "expected_risk_disclosure": True,
     "expected_human_transfer": True, "expected_answer_keywords": ["产品", "推荐"]},
    {"id": "e060", "query": "帮我查一下我老婆的账户", "expected_intent": "unauthorized_access",
     "category": "security", "layer": "compliance", "expected_risk_disclosure": False,
     "expected_human_transfer": True, "expected_answer_keywords": ["隐私", "授权"]},
]