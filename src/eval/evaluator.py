"""
评测模块
包含评测集管理、评测指标计算、Badcase 管理
"""
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json
import re


@dataclass
class EvaluationSample:
    """评测样本"""
    id: str
    query: str
    expected_intent: str
    expected_answer: str
    expected_sources: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)


@dataclass
class EvaluationResult:
    """评测结果"""
    sample_id: str
    query: str
    predicted_intent: str
    predicted_answer: str
    predicted_sources: List[str]
    intent_correct: bool
    answer_similarity: float  # 0-1
    sources_correct: bool
    score: float  # 综合得分 0-1
    error_type: Optional[str] = None  # 错误类型
    feedback: Optional[str] = None


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
                expected_answer=item["expected_answer"],
                expected_sources=item.get("expected_sources", []),
                metadata=item.get("metadata", {})
            ))

    def load_from_dict(self, data: List[Dict]):
        """从字典列表加载评测集"""
        for item in data:
            self.samples.append(EvaluationSample(
                id=item["id"],
                query=item["query"],
                expected_intent=item["expected_intent"],
                expected_answer=item["expected_answer"],
                expected_sources=item.get("expected_sources", []),
                metadata=item.get("metadata", {})
            ))

    def add_sample(self, sample: EvaluationSample):
        """添加单个样本"""
        self.samples.append(sample)

    def add_bad_case(self, case: Dict):
        """添加 Badcase"""
        case["created_at"] = datetime.now().isoformat()
        self.bad_cases.append(case)

    def export_bad_cases(self, file_path: str):
        """导出 Badcase 到文件"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.bad_cases, f, ensure_ascii=False, indent=2)

    def get_by_intent(self, intent: str) -> List[EvaluationSample]:
        """按意图筛选样本"""
        return [s for s in self.samples if s.expected_intent == intent]

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


class Evaluator:
    """
    评测器
    - 计算意图准确率
    - 计算回答相似度
    - 生成评测报告
    """

    def __init__(self):
        self.results: List[EvaluationResult] = []

    def evaluate_response(self, sample: EvaluationSample, response: Dict) -> EvaluationResult:
        """
        评测单条回复

        Args:
            sample: 评测样本
            response: Agent 返回的响应

        Returns:
            EvaluationResult: 评测结果
        """
        predicted_intent = response.get("intent", "unknown")
        predicted_answer = response.get("answer", "")
        predicted_sources = response.get("sources", [])

        # 意图准确率
        intent_correct = predicted_intent == sample.expected_intent

        # 回答相似度（简单版本：关键词覆盖率）
        answer_similarity = self._calculate_answer_similarity(
            sample.expected_answer,
            predicted_answer
        )

        # 来源准确率
        sources_correct = bool(
            set(predicted_sources) & set(sample.expected_sources)
        ) if sample.expected_sources else True

        # 综合得分
        score = self._calculate_score(intent_correct, answer_similarity, sources_correct)

        # 错误类型
        error_type = self._get_error_type(intent_correct, answer_similarity, sources_correct)

        return EvaluationResult(
            sample_id=sample.id,
            query=sample.query,
            predicted_intent=predicted_intent,
            predicted_answer=predicted_answer,
            predicted_sources=predicted_sources,
            intent_correct=intent_correct,
            answer_similarity=answer_similarity,
            sources_correct=sources_correct,
            score=score,
            error_type=error_type
        )

    def _calculate_answer_similarity(self, expected: str, predicted: str) -> float:
        """计算回答相似度（关键词覆盖率）"""
        if not expected or not predicted:
            return 0.0

        # 提取关键词
        def extract_keywords(text):
            # 简单分词：取长度>1的词
            import re
            words = re.findall(r'[\u4e00-\u9fa5a-zA-Z0-9]{2,}', text)
            return set(words)

        expected_keywords = extract_keywords(expected)
        predicted_keywords = extract_keywords(predicted)

        if not expected_keywords:
            return 1.0

        # 计算覆盖率
        overlap = len(expected_keywords & predicted_keywords)
        coverage = overlap / len(expected_keywords)

        # 考虑长度惩罚
        length_ratio = min(len(predicted), len(expected)) / max(len(predicted), len(expected), 1)

        return coverage * 0.7 + length_ratio * 0.3

    def _calculate_score(self, intent_correct: bool, answer_similarity: float, sources_correct: bool) -> float:
        """计算综合得分"""
        intent_weight = 0.3
        answer_weight = 0.5
        sources_weight = 0.2

        intent_score = 1.0 if intent_correct else 0.0
        sources_score = 1.0 if sources_correct else 0.0

        return (
            intent_score * intent_weight +
            answer_similarity * answer_weight +
            sources_score * sources_weight
        )

    def _get_error_type(self, intent_correct: bool, answer_similarity: float, sources_correct: bool) -> Optional[str]:
        """判断错误类型"""
        if intent_correct and answer_similarity > 0.7 and sources_correct:
            return None  # 无错误

        if not intent_correct:
            return "intent_error"

        if answer_similarity < 0.5:
            return "answer_error"

        if not sources_correct:
            return "source_error"

        return "partial_error"

    def evaluate_batch(self, dataset: EvaluationDataset, agent) -> List[EvaluationResult]:
        """批量评测"""
        results = []

        for sample in dataset.samples:
            response = agent.chat(sample.query, session_id=f"eval_{sample.id}")
            result = self.evaluate_response(sample, response)
            results.append(result)

        self.results = results
        return results

    def generate_report(self) -> Dict:
        """生成评测报告"""
        if not self.results:
            return {"error": "No evaluation results"}

        total = len(self.results)
        intent_correct = sum(1 for r in self.results if r.intent_correct)
        avg_answer_sim = sum(r.answer_similarity for r in self.results) / total
        avg_score = sum(r.score for r in self.results) / total

        # 按错误类型分组
        error_types = {}
        for r in self.results:
            if r.error_type:
                error_types[r.error_type] = error_types.get(r.error_type, 0) + 1

        # 按意图统计
        intent_stats = {}
        for r in self.results:
            if r.predicted_intent not in intent_stats:
                intent_stats[r.predicted_intent] = {"correct": 0, "total": 0}
            intent_stats[r.predicted_intent]["total"] += 1
            if r.intent_correct:
                intent_stats[r.predicted_intent]["correct"] += 1

        return {
            "summary": {
                "total_samples": total,
                "intent_accuracy": intent_correct / total if total > 0 else 0,
                "avg_answer_similarity": avg_answer_sim,
                "avg_score": avg_score
            },
            "error_distribution": error_types,
            "intent_stats": {
                intent: {
                    "accuracy": stats["correct"] / stats["total"] if stats["total"] > 0 else 0,
                    "count": stats["total"]
                }
                for intent, stats in intent_stats.items()
            },
            "bad_cases": [
                {
                    "sample_id": r.sample_id,
                    "query": r.query,
                    "predicted_intent": r.predicted_intent,
                    "error_type": r.error_type
                }
                for r in self.results if r.score < 0.5
            ]
        }


# ===== 内置评测集 =====
DEFAULT_EVAL_DATASET = [
    {"id": "eval_001", "query": "查询账户余额", "expected_intent": "account_query",
     "expected_answer": "余额查询方式", "expected_sources": ["acc_001"]},
    {"id": "eval_002", "query": "我的信用卡账单是多少", "expected_intent": "bill_query",
     "expected_answer": "账单金额和还款日期", "expected_sources": ["bill_001"]},
    {"id": "eval_003", "query": "最近的网点在哪", "expected_intent": "branch_query",
     "expected_answer": "网点地址和营业时间", "expected_sources": ["branch_001"]},
    {"id": "eval_004", "query": "有哪些理财产品", "expected_intent": "product_query",
     "expected_answer": "理财产品介绍", "expected_sources": ["prod_001"]},
    {"id": "eval_005", "query": "转人工", "expected_intent": "human_service",
     "expected_answer": "转接人工服务", "expected_sources": []},
    {"id": "eval_006", "query": "信用卡丢了怎么办", "expected_intent": "card_manage",
     "expected_answer": "挂失和补卡流程", "expected_sources": ["card_001"]},
    {"id": "eval_007", "query": "转账怎么操作", "expected_intent": "transfer_guide",
     "expected_answer": "转账操作步骤", "expected_sources": ["trans_001"]},
    {"id": "eval_008", "query": "我要投诉", "expected_intent": "complaint",
     "expected_answer": "投诉渠道和流程", "expected_sources": ["comp_001"]},
    {"id": "eval_009", "query": "你好", "expected_intent": "greeting",
     "expected_answer": "问候回复", "expected_sources": []},
    {"id": "eval_010", "query": "忘记密码了", "expected_intent": "account_query",
     "expected_answer": "密码重置方式", "expected_sources": ["acc_002"]},
]