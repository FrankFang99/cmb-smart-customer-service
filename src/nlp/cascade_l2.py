"""
Cascade L2 BERT 集成 (v3.6.0)
=============================
替换 v3.5.6 的 L3 LLM 兜底前的意图识别, 加 L2 BERT 分类器.

新流程:
- L1 规则 (IntentRecognizer) → 置信度 >= 0.85 → 返回
                              ↓ < 0.85
- L2 BERT (M3 微调) → 置信度 >= 0.85 → 返回
                     ↓ < 0.85
- L3 LLM 兜底 (v3.5.6 preprocess + LLM)

业界做法: 置信度门控 (Confidence Gating), 见 BERT/RoBERTa 在低延迟场景的工业部署
"""
from __future__ import annotations
import os
import sys
import time
from typing import Optional, Tuple, Dict, Any
from pathlib import Path

_PROJECT_ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class BertL2Classifier:
    """L2 BERT 分类器 - 置信度门控"""

    def __init__(self, model_path: str = None, confidence_threshold: float = 0.85):
        if model_path is None:
            # 默认 M3 路径
            model_path = os.path.join(_PROJECT_ROOT, "models", "M3-bert-base-chinese")
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.tokenizer = None
        self.model = None
        self.label2id = None
        self.id2label = None
        self._loaded = False
        self._load_time_ms = 0

    def load(self) -> bool:
        """懒加载, 第一次 predict 时调"""
        if self._loaded:
            return True
        if not os.path.exists(self.model_path):
            return False
        try:
            import torch
            from transformers import BertTokenizer, BertForSequenceClassification
            t0 = time.time()
            self.tokenizer = BertTokenizer.from_pretrained(self.model_path)
            self.model = BertForSequenceClassification.from_pretrained(self.model_path)
            label2id_path = os.path.join(self.model_path, "label2id.json")
            if os.path.exists(label2id_path):
                import json
                with open(label2id_path, encoding="utf-8") as f:
                    self.label2id = json.load(f)
                self.id2label = {v: k for k, v in self.label2id.items()}
            self._load_time_ms = (time.time() - t0) * 1000
            self._loaded = True
            print(f"  [BertL2] 加载完成: {self.model_path} ({self._load_time_ms:.0f}ms)")
            return True
        except Exception as e:
            print(f"  [BertL2] 加载失败: {e}")
            return False

    @property
    def is_available(self) -> bool:
        return os.path.exists(self.model_path) and self._loaded

    def predict(self, text: str) -> Optional[Tuple[str, float, str]]:
        """
        Returns: (intent, confidence, source) or None (未加载/失败)
        - intent: 预测意图
        - confidence: softmax 最大概率
        - source: 'L2_bert'
        """
        if not self._loaded:
            if not self.load():
                return None
        try:
            import torch
            import torch.nn.functional as F
            inputs = self.tokenizer(
                text, return_tensors="pt", truncation=True,
                max_length=16, padding="max_length"
            )
            with torch.no_grad():
                logits = self.model(**inputs).logits[0]
                probs = F.softmax(logits, dim=-1).cpu().numpy()
            top_idx = int(probs.argmax())
            intent = self.id2label[top_idx]
            conf = float(probs[top_idx])
            return (intent, conf, "L2_bert")
        except Exception as e:
            print(f"  [BertL2] predict 失败: {e}")
            return None


# Singleton
_BERT_L2_SINGLETON: Optional[BertL2Classifier] = None


def get_bert_l2() -> BertL2Classifier:
    """获取 L2 BERT 单例"""
    global _BERT_L2_SINGLETON
    if _BERT_L2_SINGLETON is None:
        _BERT_L2_SINGLETON = BertL2Classifier()
    return _BERT_L2_SINGLETON


def cascade_predict_with_l2(
    text: str,
    rule_result: Tuple[str, float],
    confidence_threshold: float = 0.85,
) -> Tuple[str, float, str, bool]:
    """
    Cascade 预测: L1 规则 → L2 BERT → L3 LLM 兜底

    Args:
        text: 用户 query
        rule_result: (rule_intent, rule_confidence)
        confidence_threshold: 置信度门限 (默认 0.85)

    Returns:
        (intent, confidence, source, use_llm_fallback)
        - source: 'L1_rule' | 'L2_bert' | 'L3_llm_pending'
        - use_llm_fallback: True = 需要 LLM 兜底
    """
    rule_intent, rule_conf = rule_result

    # L1: 规则高置信 -> 直接返回
    if rule_conf >= confidence_threshold:
        return (rule_intent, rule_conf, "L1_rule", False)

    # L2: BERT 兜底
    bert = get_bert_l2()
    if bert.is_available or bert.load():
        result = bert.predict(text)
        if result is not None:
            bert_intent, bert_conf, _ = result
            if bert_conf >= confidence_threshold:
                return (bert_intent, bert_conf, "L2_bert", False)

    # L3: LLM 兜底
    # (rule_intent 是 fallback 默认, 实际 LLM 会给新预测)
    return (rule_intent, rule_conf, "L3_llm_pending", True)
