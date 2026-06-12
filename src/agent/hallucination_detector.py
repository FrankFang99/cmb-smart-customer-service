"""
v3.5.0 幻觉检测雏形
======================

业界对齐: 蚂蚁 / 微众 / 字节 2025-2026 都在做
- Self-Check (LLM 自检)
- 检索校验 (答案 vs 知识库 Top-1)
- NLI 模型 (自然语言推理, 0 依赖下用关键词重叠)

设计:
- 3 种检测独立可观测
- 0 依赖 (NLI 用关键词重叠 mock, v4.0 接真实 NLI)
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

# ============================================================
# 中文停用词
# ============================================================
STOP_WORDS = {
    "的", "了", "和", "是", "在", "有", "我", "你", "他", "她", "它", "们",
    "请", "问", "可以", "怎么", "什么", "如何", "什么", "这", "那", "这个", "那个",
    "需要", "想", "要", "会", "可", "或", "及", "与", "或", "等", "把", "被",
    "对", "到", "从", "给", "和", "与", "为", "为了", "因为", "所以",
    "啊", "吧", "呢", "吗", "哦", "嗯", "哈", "呀",
}


def _tokenize(text: str) -> List[str]:
    """简单中文分词 (按字符 2-gram + 标点切分)"""
    text = re.sub(r"[^\w\u4e00-\u9fa5]+", " ", text)
    tokens = []
    for word in text.split():
        if len(word) >= 2 and not all(c in STOP_WORDS for c in word):
            tokens.append(word)
        # 2-gram
        for i in range(len(word) - 1):
            bigram = word[i:i + 2]
            if not all(c in STOP_WORDS for c in bigram):
                tokens.append(bigram)
    return tokens


# ============================================================
# 1. 关键词重叠检测 (NLI mock)
# ============================================================
class KeywordOverlapChecker:
    """关键词重叠检测 (NLI mock, 0 依赖)"""

    def __init__(self, threshold: float = 0.3):
        self.threshold = threshold

    def check(
        self, answer: str, evidence: str
    ) -> Dict[str, Any]:
        """
        检查答案和证据的关键词重叠
        Returns: {
            "supported": bool,
            "score": float (0-1),
            "overlap_words": list,
        }
        """
        ans_tokens = set(_tokenize(answer))
        evi_tokens = set(_tokenize(evidence))
        if not ans_tokens or not evi_tokens:
            return {"supported": False, "score": 0.0, "overlap_words": []}
        overlap = ans_tokens & evi_tokens
        # 双向归一化
        precision = len(overlap) / len(ans_tokens) if ans_tokens else 0
        recall = len(overlap) / len(evi_tokens) if evi_tokens else 0
        score = (precision + recall) / 2.0
        return {
            "supported": score >= self.threshold,
            "score": round(score, 3),
            "overlap_words": list(overlap)[:10],
        }


# ============================================================
# 2. 数字/事实校验
# ============================================================
class NumberFactChecker:
    """数字/事实校验 (检测答案中的数字是否在证据里)"""

    def check(
        self, answer: str, evidence: str
    ) -> Dict[str, Any]:
        """
        检查数字事实
        Returns: {
            "supported": bool,
            "numbers_in_answer": list,
            "numbers_in_evidence": list,
            "unsupported_numbers": list,
        }
        """
        # 提取数字
        ans_nums = re.findall(r"\d+\.?\d*", answer)
        evi_nums = re.findall(r"\d+\.?\d*", evidence)
        # 数字归一化
        ans_nums_set = {n.rstrip("0").rstrip(".") if "." in n else n for n in ans_nums}
        evi_nums_set = {n.rstrip("0").rstrip(".") if "." in n else n for n in evi_nums}
        # 不在证据中的数字
        unsupported = ans_nums_set - evi_nums_set
        # 排除常见非事实数字 (年/月/日)
        unsupported = {
            n for n in unsupported
            if not (
                n in {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9"}
                or any(kw in answer for kw in ["1年", "12期", "24期", "36期"])  # 模糊
            )
        }
        return {
            "supported": len(unsupported) == 0,
            "numbers_in_answer": list(ans_nums_set),
            "numbers_in_evidence": list(evi_nums_set),
            "unsupported_numbers": list(unsupported),
        }


# ============================================================
# 3. 关键词禁止检测 (检测答案中是否含禁止词)
# ============================================================
FORBIDDEN_PHRASES = [
    "我无法",
    "我不太清楚",
    "我不知道",
    "请咨询专业人士",
    "请咨询专业机构",
    "作为 AI",
    "作为一个 AI",
    "我是 AI",
    "我不具备",
    "我无法提供",
    "sorry",
    "I am sorry",
    "I'm sorry",
    "保证收益",
    "100% 安全",
    "100% 通过",
    "百分百",
    "无风险",
    "保本保息",
]


class PhraseForbiddenChecker:
    """禁止词检测 (LLM 容易出现的禁用语)"""

    def __init__(self, forbidden: Optional[List[str]] = None):
        self.forbidden = forbidden or FORBIDDEN_PHRASES

    def check(self, answer: str) -> Dict[str, Any]:
        """检查答案中是否含禁止词"""
        found = []
        for phrase in self.forbidden:
            if phrase.lower() in answer.lower():
                found.append(phrase)
        return {
            "supported": len(found) == 0,
            "forbidden_phrases": found,
        }


# ============================================================
# 4. 综合幻觉检测器
# ============================================================
class HallucinationDetector:
    """综合幻觉检测器 (3 个检测器组合)"""

    def __init__(self):
        self.overlap = KeywordOverlapChecker()
        self.number = NumberFactChecker()
        self.forbidden = PhraseForbiddenChecker()

    def detect(
        self, answer: str, evidence: str = "", intent: str = ""
    ) -> Dict[str, Any]:
        """
        综合检测
        Returns: {
            "is_hallucination": bool,
            "score": float (0-1, 越高越像幻觉),
            "checks": {
                "overlap": {...},
                "number": {...},
                "forbidden": {...},
            },
            "action": "pass" | "warn" | "fallback_template",
        }
        """
        checks = {}
        if evidence:
            checks["overlap"] = self.overlap.check(answer, evidence)
            checks["number"] = self.number.check(answer, evidence)
        checks["forbidden"] = self.forbidden.check(answer)
        # 综合分数
        hallucination_score = 0.0
        if evidence:
            if not checks["overlap"]["supported"]:
                hallucination_score += 0.4
            if not checks["number"]["supported"]:
                hallucination_score += 0.4
        if not checks["forbidden"]["supported"]:
            hallucination_score += 0.3
        hallucination_score = min(hallucination_score, 1.0)
        # 动作
        if hallucination_score < 0.2:
            action = "pass"
        elif hallucination_score < 0.5:
            action = "warn"
        else:
            action = "fallback_template"
        return {
            "is_hallucination": hallucination_score >= 0.5,
            "score": round(hallucination_score, 3),
            "checks": checks,
            "action": action,
        }


# ============================================================
# 工厂
# ============================================================
def get_hallucination_detector() -> HallucinationDetector:
    """获取幻觉检测器"""
    return HallucinationDetector()
