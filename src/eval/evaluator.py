"""
璇勬祴妯″潡
鍖呭惈璇勬祴闆嗙鐞嗐€佽瘎娴嬫寚鏍囪绠椼€丅adcase 绠＄悊
"""
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json
import re


@dataclass
class EvaluationSample:
    """璇勬祴鏍锋湰"""
    id: str
    query: str
    expected_intent: str
    expected_answer: str
    expected_sources: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)


@dataclass
class EvaluationResult:
    """璇勬祴缁撴灉"""
    sample_id: str
    query: str
    predicted_intent: str
    predicted_answer: str
    predicted_sources: List[str]
    intent_correct: bool
    answer_similarity: float  # 0-1
    sources_correct: bool
    score: float  # 缁煎悎寰楀垎 0-1
    error_type: Optional[str] = None  # 閿欒绫诲瀷
    feedback: Optional[str] = None


class EvaluationDataset:
    """
    璇勬祴鏁版嵁闆嗙鐞?    - 鍔犺浇璇勬祴闆?    - 绉嶅瓙闂鎵╁睍
    - Badcase 绠＄悊
    """

    def __init__(self):
        self.samples: List[EvaluationSample] = []
        self.bad_cases: List[Dict] = []

    def load_from_json(self, file_path: str):
        """浠?JSON 鏂囦欢鍔犺浇璇勬祴闆?""
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
        """浠庡瓧鍏稿垪琛ㄥ姞杞借瘎娴嬮泦"""
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
        """娣诲姞鍗曚釜鏍锋湰"""
        self.samples.append(sample)

    def add_bad_case(self, case: Dict):
        """娣诲姞 Badcase"""
        case["created_at"] = datetime.now().isoformat()
        self.bad_cases.append(case)

    def export_bad_cases(self, file_path: str):
        """瀵煎嚭 Badcase 鍒版枃浠?""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.bad_cases, f, ensure_ascii=False, indent=2)

    def get_by_intent(self, intent: str) -> List[EvaluationSample]:
        """鎸夋剰鍥剧瓫閫夋牱鏈?""
        return [s for s in self.samples if s.expected_intent == intent]

    def generate_seed_expansions(self, seed_queries: List[str], n_variations: int = 5) -> List[str]:
        """
        绉嶅瓙闂鎵╁睍
        浣跨敤鍚屼箟璇嶃€佸彞寮忓彉鎹㈢瓑鏂瑰紡鐢熸垚鐩镐技闂
        """
        expansions = []

        for query in seed_queries:
            # 绠€鍗曡鍒欐墿灞?            variations = [
                query,  # 鍘熷彞
                f"璇烽棶{query}",  # 鍔犺闂?                f"{query}鍚?,  # 鍔犲悧
                f"鎴戞兂{query}",  # 鍔犳垜鎯?                f"鎬庝箞{query}",  # 鏀规垚鎬庝箞
                query.replace("锛?, "").replace("?", ""),  # 鍘婚棶鍙?            ]
            expansions.extend(variations[:n_variations])

        return expansions


class Evaluator:
    """
    璇勬祴鍣?    - 璁＄畻鎰忓浘鍑嗙‘鐜?    - 璁＄畻鍥炵瓟鐩镐技搴?    - 鐢熸垚璇勬祴鎶ュ憡
    """

    def __init__(self):
        self.results: List[EvaluationResult] = []

    def evaluate_response(self, sample: EvaluationSample, response: Dict) -> EvaluationResult:
        """
        璇勬祴鍗曟潯鍥炲

        Args:
            sample: 璇勬祴鏍锋湰
            response: Agent 杩斿洖鐨勫搷搴?
        Returns:
            EvaluationResult: 璇勬祴缁撴灉
        """
        predicted_intent = response.get("intent", "unknown")
        predicted_answer = response.get("answer", "")
        predicted_sources = response.get("sources", [])

        # 鎰忓浘鍑嗙‘鐜?        intent_correct = predicted_intent == sample.expected_intent

        # 鍥炵瓟鐩镐技搴︼紙绠€鍗曠増鏈細鍏抽敭璇嶈鐩栫巼锛?        answer_similarity = self._calculate_answer_similarity(
            sample.expected_answer,
            predicted_answer
        )

        # 鏉ユ簮鍑嗙‘鐜?        sources_correct = bool(
            set(predicted_sources) & set(sample.expected_sources)
        ) if sample.expected_sources else True

        # 缁煎悎寰楀垎
        score = self._calculate_score(intent_correct, answer_similarity, sources_correct)

        # 閿欒绫诲瀷
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
        """璁＄畻鍥炵瓟鐩镐技搴︼紙鍏抽敭璇嶈鐩栫巼锛?""
        if not expected or not predicted:
            return 0.0

        # 鎻愬彇鍏抽敭璇?        def extract_keywords(text):
            # 绠€鍗曞垎璇嶏細鍙栭暱搴?1鐨勮瘝
            import re
            words = re.findall(r'[\u4e00-\u9fa5a-zA-Z0-9]{2,}', text)
            return set(words)

        expected_keywords = extract_keywords(expected)
        predicted_keywords = extract_keywords(predicted)

        if not expected_keywords:
            return 1.0

        # 璁＄畻瑕嗙洊鐜?        overlap = len(expected_keywords & predicted_keywords)
        coverage = overlap / len(expected_keywords)

        # 鑰冭檻闀垮害鎯╃綒
        length_ratio = min(len(predicted), len(expected)) / max(len(predicted), len(expected), 1)

        return coverage * 0.7 + length_ratio * 0.3

    def _calculate_score(self, intent_correct: bool, answer_similarity: float, sources_correct: bool) -> float:
        """璁＄畻缁煎悎寰楀垎"""
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
        """鍒ゆ柇閿欒绫诲瀷"""
        if intent_correct and answer_similarity > 0.7 and sources_correct:
            return None  # 鏃犻敊璇?
        if not intent_correct:
            return "intent_error"

        if answer_similarity < 0.5:
            return "answer_error"

        if not sources_correct:
            return "source_error"

        return "partial_error"

    def evaluate_batch(self, dataset: EvaluationDataset, agent) -> List[EvaluationResult]:
        """鎵归噺璇勬祴"""
        results = []

        for sample in dataset.samples:
            response = agent.chat(sample.query, session_id=f"eval_{sample.id}")
            result = self.evaluate_response(sample, response)
            results.append(result)

        self.results = results
        return results

    def generate_report(self) -> Dict:
        """鐢熸垚璇勬祴鎶ュ憡"""
        if not self.results:
            return {"error": "No evaluation results"}

        total = len(self.results)
        intent_correct = sum(1 for r in self.results if r.intent_correct)
        avg_answer_sim = sum(r.answer_similarity for r in self.results) / total
        avg_score = sum(r.score for r in self.results) / total

        # 鎸夐敊璇被鍨嬪垎缁?        error_types = {}
        for r in self.results:
            if r.error_type:
                error_types[r.error_type] = error_types.get(r.error_type, 0) + 1

        # 鎸夋剰鍥剧粺璁?        intent_stats = {}
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


# ===== 鍐呯疆璇勬祴闆?=====
DEFAULT_EVAL_DATASET = [
    {"id": "eval_001", "query": "鏌ヨ璐︽埛浣欓", "expected_intent": "account_query",
     "expected_answer": "浣欓鏌ヨ鏂瑰紡", "expected_sources": ["acc_001"]},
    {"id": "eval_002", "query": "鎴戠殑淇＄敤鍗¤处鍗曟槸澶氬皯", "expected_intent": "bill_query",
     "expected_answer": "璐﹀崟閲戦鍜岃繕娆炬棩鏈?, "expected_sources": ["bill_001"]},
    {"id": "eval_003", "query": "鏈€杩戠殑缃戠偣鍦ㄥ摢", "expected_intent": "branch_query",
     "expected_answer": "缃戠偣鍦板潃鍜岃惀涓氭椂闂?, "expected_sources": ["branch_001"]},
    {"id": "eval_004", "query": "鏈夊摢浜涚悊璐骇鍝?, "expected_intent": "product_query",
     "expected_answer": "鐞嗚储浜у搧浠嬬粛", "expected_sources": ["prod_001"]},
    {"id": "eval_005", "query": "杞汉宸?, "expected_intent": "human_service",
     "expected_answer": "杞帴浜哄伐鏈嶅姟", "expected_sources": []},
    {"id": "eval_006", "query": "淇＄敤鍗′涪浜嗘€庝箞鍔?, "expected_intent": "card_manage",
     "expected_answer": "鎸傚け鍜岃ˉ鍗℃祦绋?, "expected_sources": ["card_001"]},
    {"id": "eval_007", "query": "杞处鎬庝箞鎿嶄綔", "expected_intent": "transfer_guide",
     "expected_answer": "杞处鎿嶄綔姝ラ", "expected_sources": ["trans_001"]},
    {"id": "eval_008", "query": "鎴戣鎶曡瘔", "expected_intent": "complaint",
     "expected_answer": "鎶曡瘔娓犻亾鍜屾祦绋?, "expected_sources": ["comp_001"]},
    {"id": "eval_009", "query": "浣犲ソ", "expected_intent": "greeting",
     "expected_answer": "闂€欏洖澶?, "expected_sources": []},
    {"id": "eval_010", "query": "蹇樿瀵嗙爜浜?, "expected_intent": "account_query",
     "expected_answer": "瀵嗙爜閲嶇疆鏂瑰紡", "expected_sources": ["acc_002"]},
]