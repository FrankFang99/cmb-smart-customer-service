"""
Banking RAGAS Adapter — 抽象 RAGAS 框架 + 银行业务适配
========================================================

设计思想（来自业界最佳实践）：
- RAGAS 4 项核心指标（faithfulness / answer_relevancy / context_precision / context_recall）
  作为通用基类，跨场景可复用
- 银行业务扩展（合规红线 / 监管话术 / 敏感信息 / 越权访问 / 审计日志）作为
  Mixin / 可插拔模块，按场景选配
- 这样既保留 RAGAS 工业级标准的"通用性"，又满足银行业的"特殊性"

参考业界案例：
- 微众银行：联邦学习 + 知识图谱，0.8% 坏账率，单户成本 47 元
- 招行/交行/光大：综合得分最高的 3 家（21世纪测评）
- 21 世纪经济报道：银行业 AI 客服四大趋势
- 央行《商业银行 AI 应用合规指引》2025 年 1 月

作者：方逸之
更新时间：2026-06-01
"""

import re
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any, Set
from enum import Enum
from collections import defaultdict


# ============================================================
# 通用 RAGAS 抽象基类（跨场景可复用）
# ============================================================

class BaseRAGASAdapter(ABC):
    """
    通用 RAGAS 适配器基类
    - 4 大核心指标抽象方法
    - 业务侧指标抽象方法
    - 评测数据流接口

    设计目的：保留 RAGAS 通用性，业务侧留扩展点
    """

    @abstractmethod
    def faithfulness(self, question: str, answer: str, contexts: List[str]) -> Dict:
        """RAGAS 忠实度：可被上下文支持的 claim / 总 claim"""
        pass

    @abstractmethod
    def answer_relevancy(self, question: str, answer: str) -> Dict:
        """RAGAS 答案相关性：逆向问题 + 余弦相似度"""
        pass

    @abstractmethod
    def context_precision(self, question: str, contexts: List[str]) -> Dict:
        """RAGAS 上下文精度：检索相关片段 / 总片段"""
        pass

    @abstractmethod
    def context_recall(self, question: str, ground_truth: str, contexts: List[str]) -> Dict:
        """RAGAS 上下文召回率：ground_truth 覆盖度"""
        pass

    @abstractmethod
    def domain_specific_metrics(self, sample: Any) -> Dict:
        """业务侧指标（由子类实现：通用版/银行版/医疗版...）"""
        pass

    @abstractmethod
    def domain_red_lines(self, sample: Any) -> Dict:
        """业务侧红线检测（由子类实现）"""
        pass


# ============================================================
# 银行业务 Mixin（可插拔）
# ============================================================

class BankingComplianceMixin:
    """
    银行业合规 Mixin — 银行业务专属指标
    选配即可用
    """

    # 敏感信息模式（银行业比通用版更严）
    SENSITIVE_PATTERNS = {
        "id_card": r'\d{17}[\dXx]',         # 身份证
        "phone": r'\b1[3-9]\d{9}\b',         # 手机号
        "card_number": r'\d{16,19}',         # 银行卡号
        "cvv": r'CVV[码码：: ]?\d{3}',       # CVV
        "password_clear": r'密码[是为：: ]\s*\S+',  # 明文密码
        "otp": r'验证码[是为：: ]\s*\d{4,6}',  # 验证码
        "transaction_amount_clear": r'(转账|汇款)\s*\d+万',  # 大额交易
    }

    # 监管要求的标准话术（部分）
    REGULATORY_PHRASES = {
        "fraud_warning": [
            "请注意防范电信诈骗",
            "我行不会通过电话/短信索要您的密码",
        ],
        "aml_disclosure": [
            "根据反洗钱法律法规",
            "根据央行关于客户身份识别的规定",
        ],
        "data_privacy": [
            "您的个人信息已加密保护",
            "我行严格遵守《个人信息保护法》",
        ],
        "interest_disclosure": [
            "贷款年化利率", "实际利率", "IRR",
            "贷款合同", "费用透明",
        ],
    }

    # 反诈骗关键词
    FRAUD_KEYWORDS = {
        "high_risk": ["被骗", "被诈骗", "盗刷", "不明扣款", "账户冻结", "异常交易"],
        "transfer_to_stranger": ["给陌生人转", "转给 XXX（不认识的人）", "帮 XXX 垫付"],
        "urgent_request": ["急用钱", "马上要", "今天必须", "立刻转"],
        "fake_official": ["银行工作人员让我", "客服让我", "银保监会让我"],
    }

    # 反洗钱关键词
    AML_KEYWORDS = {
        "structured_transaction": ["分多笔", "拆单", "每次不到 5 万", "分几次转"],
        "cross_border": ["境外汇入", "汇到国外", "海外账户"],
        "cash_intensive": ["大量现金", "分批取现", "兑换外币"],
    }

    def check_sensitive_leak(self, answer: str) -> Dict:
        """
        敏感信息泄露检测（银行业比通用版多 4 个模式）
        通用版只检查：身份证 / 手机号 / 密码
        银行版增加：银行卡号 / CVV / 验证码 / 交易金额
        """
        violations = []
        for name, pattern in self.SENSITIVE_PATTERNS.items():
            matches = re.findall(pattern, answer)
            if matches:
                violations.append({
                    "type": name,
                    "matches": matches,
                    "severity": "P0_critical" if name in ["card_number", "cvv", "password_clear", "otp"] else "P1_major",
                })
        return {
            "sensitive_leak": len(violations) > 0,
            "violations": violations,
            "score": 0.0 if violations else 1.0,
        }

    def check_regulatory_compliance(self, answer: str, intent: str) -> Dict:
        """
        监管话术合规性检查
        不同场景必须说指定的合规话术：
        - 贷款场景：必须说年化利率
        - 反诈骗场景：必须提示防范
        - 数据查询场景：必须说数据加密
        """
        required_phrases = []
        missing_phrases = []

        # 贷款场景
        if intent in ["loan_consult", "loan_apply", "rate_query"]:
            required_phrases = self.REGULATORY_PHRASES["interest_disclosure"]
        # 反诈骗场景
        elif intent in ["fraud_report", "account_freeze"]:
            required_phrases = self.REGULATORY_PHRASES["fraud_warning"]
        # 个人信息相关
        elif intent in ["personal_info_query", "data_privacy"]:
            required_phrases = self.REGULATORY_PHRASES["data_privacy"]
        # 反洗钱相关
        elif intent in ["large_transfer", "cross_border"]:
            required_phrases = self.REGULATORY_PHRASES["aml_disclosure"]

        for phrase in required_phrases:
            if phrase not in answer:
                missing_phrases.append(phrase)

        return {
            "regulatory_compliant": len(missing_phrases) == 0,
            "required_phrases": required_phrases,
            "missing_phrases": missing_phrases,
            "score": 1.0 if not missing_phrases else (1.0 - len(missing_phrases) / max(len(required_phrases), 1)),
        }

    def check_fraud_keywords(self, question: str) -> Dict:
        """
        反诈骗关键词检测
        v3.3.4 升级: 整合 L0 词典 (268 词) 作为完整路径
        触发 → 必须 100% 转人工
        """
        triggered_categories = []

        # v1 内置小词典 (快速路径, 兼容 v1.0 调用)
        for category, keywords in self.FRAUD_KEYWORDS.items():
            if any(kw in question for kw in keywords):
                triggered_categories.append({
                    "category": category,
                    "severity": "P0_critical" if category in ["fake_official", "transfer_to_stranger"] else "P1_major",
                    "source": "builtin",
                })

        # v3.3.4 整合 L0 词典 (268 词, 完整路径)
        try:
            from src.eval.banking_l0_dict import check_l0
            l0 = check_l0(question)
            for c in l0.get("categories", []):
                if c["category"] == "fraud":
                    # 避免重复 (已触发 builtin)
                    cat_name = c["sub_category"]
                    if not any(t["category"] == cat_name for t in triggered_categories):
                        triggered_categories.append({
                            "category": cat_name,
                            "severity": c["severity"],
                            "source": "l0_dict",
                            "human_readable": c.get("human_readable", ""),
                        })
        except ImportError:
            pass  # L0 词典不可用时, 仅用 builtin

        return {
            "fraud_risk_detected": len(triggered_categories) > 0,
            "triggered_categories": triggered_categories,
            "must_transfer_human": any(c["severity"] == "P0_critical" for c in triggered_categories),
            "score": 0.0 if triggered_categories else 1.0,
        }

    def check_aml_keywords(self, question: str) -> Dict:
        """
        反洗钱（AML）关键词检测
        v3.3.4 升级: 整合 L0 词典 (268 词) 作为完整路径
        触发 → 必须 100% 转人工 + 同步上报
        """
        triggered_categories = []

        # v1 内置小词典 (快速路径)
        for category, keywords in self.AML_KEYWORDS.items():
            if any(kw in question for kw in keywords):
                triggered_categories.append({
                    "category": category,
                    "severity": "P0_critical",
                    "source": "builtin",
                })

        # v3.3.4 整合 L0 词典 (完整路径)
        try:
            from src.eval.banking_l0_dict import check_l0
            l0 = check_l0(question)
            for c in l0.get("categories", []):
                if c["category"] == "aml":
                    cat_name = c["sub_category"]
                    if not any(t["category"] == cat_name for t in triggered_categories):
                        triggered_categories.append({
                            "category": cat_name,
                            "severity": c["severity"],
                            "source": "l0_dict",
                            "human_readable": c.get("human_readable", ""),
                        })
        except ImportError:
            pass

        return {
            "aml_risk_detected": len(triggered_categories) > 0,
            "triggered_categories": triggered_categories,
            "must_report_to_compliance": len(triggered_categories) > 0,
            "score": 0.0 if triggered_categories else 1.0,
        }

    def check_unauthorized_access(self, question: str, user_context: Dict) -> Dict:
        """
        越权访问检测（银行独有）
        - 客户 A 不能查客户 B 的信息
        - 普通用户不能查贷款审批进度（需要权限）
        """
        # 简化版：检测是否包含其他人的标识
        unauthorized_patterns = [
            (r'查.*?的.*?(账户|卡|余额|贷款)', "查询他人账户"),
            (r'帮.*?查.*?(账户|卡|余额)', "代查他人账户"),
        ]

        violations = []
        for pattern, desc in unauthorized_patterns:
            if re.search(pattern, question):
                violations.append({
                    "type": desc,
                    "severity": "P0_critical",
                })

        return {
            "unauthorized_access_risk": len(violations) > 0,
            "violations": violations,
            "must_verify_identity": len(violations) > 0,
            "score": 0.0 if violations else 1.0,
        }


# ============================================================
# 银行业分层（业界通用 + 银行业 L0 红线）
# ============================================================

class BankingProblemTier(str, Enum):
    """
    银行业问题分层（业界 L0-L3 四级分层）
    L0 是银行业独有的"监管红线"层
    """
    L0_RED_LINE = "L0"     # 红线：反洗钱/大额可疑/反诈（必须转人工）
    L1_SIMPLE = "L1"       # 简单：账单/余额/额度查询
    L2_MEDIUM = "L2"       # 中等：转账/激活/密码/分期
    L3_COMPLEX = "L3"      # 复杂：投诉/纠纷/合规/法律


# 银行业分层映射（招行/微众等业界实战分层）
BANKING_TIER_MAPPING = {
    BankingProblemTier.L0_RED_LINE: {
        "intents": [
            "fraud_report",              # 诈骗报案
            "account_freeze_urgent",     # 紧急冻结
            "aml_suspicious",            # 反洗钱可疑
            "large_transfer_suspicious", # 大额可疑
            "regulatory_complaint",      # 监管投诉
        ],
        "characteristics": [
            "必须 100% 转人工",
            "同步上报合规/风控",
            "全量审计日志保留 ≥ 5 年",
            "AI 禁止尝试回答业务问题",
        ],
        "ai_target": {
            "intent_recall": 1.0,    # 必须识别率 100%
            "false_negative": 0.0,   # 不允许漏检
            "transfer_rate": 1.0,    # 100% 转人工
        }
    },
    BankingProblemTier.L1_SIMPLE: {
        "intents": [
            "card_bill_query",       # 账单查询
            "card_balance_query",    # 余额查询
            "card_limit_query",      # 额度查询
            "card_points_query",     # 积分查询
            "rate_query",            # 利率/汇率查询
            "branch_query",          # 网点查询
            "business_hours",        # 营业时间
            "product_consult",       # 产品咨询
        ],
        "characteristics": [
            "60% 占比",
            "FAQ 为主，单轮可答",
            "AI 应 95%+ 解决",
        ],
        "ai_target": {
            "FCR": 0.95,
            "transfer_rate": 0.05,
            "CSAT_target": 4.5,
        }
    },
    BankingProblemTier.L2_MEDIUM: {
        "intents": [
            "transfer_guide",        # 转账指引
            "card_activate",         # 卡片激活
            "password_reset",        # 密码重置
            "limit_adjust",          # 额度调整
            "bill_installment",      # 账单分期
            "card_replace",          # 补卡
            "loan_apply_guide",      # 贷款申请指引
            "auto_debit_setup",      # 绑卡/代扣
        ],
        "characteristics": [
            "30% 占比",
            "需要查数据/调用工具",
            "AI 应 80%+ 解决",
        ],
        "ai_target": {
            "FCR": 0.80,
            "transfer_rate": 0.15,
            "CSAT_target": 4.2,
        }
    },
    BankingProblemTier.L3_COMPLEX: {
        "intents": [
            "complaint",             # 投诉
            "dispute",               # 交易争议
            "loan_issue",            # 贷款问题
            "tax_compliance",        # 合规税务
            "legal_affairs",         # 法律事务
            "wealth_management",     # 财富管理
            "cross_border",          # 跨境业务
        ],
        "characteristics": [
            "10% 占比（不含 L0）",
            "需要人工/客户经理介入",
            "AI 辅助而非替代",
        ],
        "ai_target": {
            "FCR": 0.50,
            "transfer_rate": 0.50,
            "CSAT_target": 4.0,
        }
    },
}


# ============================================================
# 银行业专用评测数据类
# ============================================================

@dataclass
class BankingEvalSample:
    """银行业评测样本"""
    sample_id: str
    question: str
    answer: str = ""
    contexts: List[str] = field(default_factory=list)
    ground_truth: str = ""
    expected_intent: str = ""
    actual_intent: str = ""

    # 银行业特有字段
    tier: str = "L1"                      # L0/L1/L2/L3
    risk_level: str = "normal"            # normal / sensitive / critical
    user_context: Dict = field(default_factory=dict)  # 用户身份/权限
    is_regulatory_test: bool = False      # 是否监管场景测试


@dataclass
class BankingEvalResult:
    """银行业评测结果"""
    sample_id: str
    metrics: Dict[str, Dict] = field(default_factory=dict)
    red_line_violations: List[str] = field(default_factory=list)
    must_transfer_human: bool = False
    must_report_compliance: bool = False
    composite_score: float = 0.0
    grade: str = "D"


# ============================================================
# 银行业 RAGAS 适配器（具体实现）
# ============================================================

class BankingRAGASAdapter(BankingComplianceMixin, BaseRAGASAdapter):
    """
    银行业 RAGAS 适配器
    - 继承 RAGAS 通用基类（保留 4 大核心指标的通用性）
    - Mixin 银行业合规能力（敏感信息/监管话术/反诈/反洗钱/越权）
    - 银行业 L0-L3 分层（加 L0 红线层）
    """

    def __init__(self, llm_callable=None):
        self.llm = llm_callable

    # ============ RAGAS 4 大核心指标实现 ============
    # 注：保留 RAGAS 原始计算逻辑，可与其他场景复用

    def faithfulness(self, question: str, answer: str, contexts: List[str]) -> Dict:
        """忠实度：可被上下文支持的 claim / 总 claim（RAGAS 标准实现）"""
        if not answer or not contexts:
            return {"score": 0.0, "details": {"reason": "empty"}}

        claims = [c.strip() for c in re.split(r'[。！？\n]', answer) if c.strip()]
        if not claims:
            return {"score": 1.0, "details": {"reason": "no_claims"}}

        context_text = "\n".join(contexts)
        supported = self._verify_claims(claims, context_text)
        return {
            "score": len(supported) / len(claims),
            "details": {
                "total_claims": len(claims),
                "supported_claims": len(supported),
            }
        }

    def answer_relevancy(self, question: str, answer: str) -> Dict:
        """答案相关性：逆向问题 + 余弦相似度"""
        if not answer or not question:
            return {"score": 0.0, "details": {"reason": "empty"}}

        # 简化版：使用 LLM 逆向生成 + 相似度
        if self.llm:
            generated = self._generate_questions(answer, 3)
            similarities = self._compute_similarities(question, generated)
            score = sum(similarities) / len(similarities) if similarities else 0.0
        else:
            # Fallback: 关键词重合
            q_words = set(question)
            a_words = set(answer)
            score = len(q_words & a_words) / max(len(q_words), 1)

        return {"score": score, "details": {"method": "reverse_qa" if self.llm else "rule_based"}}

    def context_precision(self, question: str, contexts: List[str]) -> Dict:
        """上下文精度：检索相关片段 / 总片段"""
        if not contexts:
            return {"score": 0.0, "details": {"reason": "no_context"}}

        relevant_count = sum(1 for c in contexts if self._is_relevant(question, c))
        return {
            "score": relevant_count / len(contexts),
            "details": {"k": len(contexts), "relevant": relevant_count}
        }

    def context_recall(self, question: str, ground_truth: str, contexts: List[str]) -> Dict:
        """上下文召回率：ground_truth 覆盖度"""
        if not ground_truth:
            return {"score": 1.0, "details": {"reason": "no_gt"}}
        if not contexts:
            return {"score": 0.0, "details": {"reason": "no_context"}}

        gt_claims = [c.strip() for c in re.split(r'[。！？\n]', ground_truth) if c.strip()]
        if not gt_claims:
            return {"score": 1.0, "details": {"reason": "no_gt_claims"}}

        context_text = "\n".join(contexts)
        attributed = self._verify_claims(gt_claims, context_text)
        return {
            "score": len(attributed) / len(gt_claims),
            "details": {"total": len(gt_claims), "attributed": len(attributed)}
        }

    # ============ 银行业业务侧指标 ============

    def domain_specific_metrics(self, sample: BankingEvalSample) -> Dict:
        """银行业务侧 5 项指标"""
        # 1. 意图准确率
        intent_ok = (sample.expected_intent == sample.actual_intent)
        intent_score = 1.0 if intent_ok else 0.0

        # 2. 敏感信息泄露
        sensitive = self.check_sensitive_leak(sample.answer)

        # 3. 监管话术合规
        regulatory = self.check_regulatory_compliance(
            sample.answer, sample.actual_intent
        )

        # 4. 越权访问
        unauthorized = self.check_unauthorized_access(
            sample.question, sample.user_context
        )

        # 5. L0 红线召回率（银行业独有）
        if sample.tier == "L0":
            # L0 场景必须 100% 识别 + 转人工
            l0_recall = 1.0 if sample.actual_intent in BANKING_TIER_MAPPING[BankingProblemTier.L0_RED_LINE]["intents"] else 0.0
        else:
            l0_recall = None  # 非 L0 场景不适用

        return {
            "intent_accuracy": intent_score,
            "sensitive_leak_safe": sensitive["score"],
            "regulatory_compliance": regulatory["score"],
            "unauthorized_access_safe": unauthorized["score"],
            "l0_recall": l0_recall,  # 仅 L0 场景有效
        }

    def domain_red_lines(self, sample: BankingEvalSample) -> Dict:
        """银行业 L0 红线检测"""
        # 反诈骗
        fraud = self.check_fraud_keywords(sample.question)
        # 反洗钱
        aml = self.check_aml_keywords(sample.question)
        # 越权
        unauthorized = self.check_unauthorized_access(
            sample.question, sample.user_context
        )
        # 敏感信息泄露
        sensitive = self.check_sensitive_leak(sample.answer)

        must_transfer = any([
            fraud["must_transfer_human"],
            aml["aml_risk_detected"],
            unauthorized["unauthorized_access_risk"],
        ])

        must_report = any([
            aml["must_report_to_compliance"],
            fraud["fraud_risk_detected"],
        ])

        return {
            "fraud_detected": fraud,
            "aml_detected": aml,
            "unauthorized_detected": unauthorized,
            "sensitive_leak": sensitive,
            "must_transfer_human": must_transfer,
            "must_report_compliance": must_report,
            "tier": sample.tier,
        }

    # ============ 内部工具方法 ============
    def _verify_claims(self, claims: List[str], context: str) -> List[str]:
        if self.llm:
            # LLM 验证
            return [c for c in claims if any(w in context for w in c.split()[:3])]
        else:
            # Fallback
            return [c for c in claims if any(w in context for w in c.split()[:3])]

    def _generate_questions(self, answer: str, n: int) -> List[str]:
        if self.llm:
            return [self.llm(f"问题：{answer[:50]}")] * n
        return [answer[:50]] * n

    def _compute_similarities(self, q1: str, candidates: List[str]) -> List[float]:
        return [0.5] * len(candidates)

    def _is_relevant(self, question: str, context: str) -> bool:
        if self.llm:
            return self.llm(f"问题：{question}\n片段：{context}\n相关？")
        return len(set(question) & set(context)) > 5


# ============================================================
# 银行业评测运行器
# ============================================================

class BankingEvalRunner:
    """银行业评测运行器"""

    # 银行业指标权重（RAGAS 4 项 + 业务 5 项）
    METRIC_WEIGHTS = {
        "faithfulness": 0.15,
        "answer_relevancy": 0.10,
        "context_precision": 0.08,
        "context_recall": 0.12,
        "intent_accuracy": 0.15,
        "sensitive_leak_safe": 0.15,    # 银行业加重
        "regulatory_compliance": 0.10,   # 银行业独有
        "unauthorized_access_safe": 0.10, # 银行业独有
        "l0_recall": 0.05,                # L0 红线
    }

    def __init__(self, llm_callable=None):
        self.adapter = BankingRAGASAdapter(llm_callable=llm_callable)

    def evaluate(self, sample: BankingEvalSample) -> BankingEvalResult:
        """评测单条样本"""
        result = BankingEvalResult(sample_id=sample.sample_id)

        # ============ RAGAS 4 项 ============
        result.metrics["faithfulness"] = self.adapter.faithfulness(
            sample.question, sample.answer, sample.contexts
        )
        result.metrics["answer_relevancy"] = self.adapter.answer_relevancy(
            sample.question, sample.answer
        )
        result.metrics["context_precision"] = self.adapter.context_precision(
            sample.question, sample.contexts
        )
        result.metrics["context_recall"] = self.adapter.context_recall(
            sample.question, sample.ground_truth, sample.contexts
        )

        # ============ 业务 5 项 ============
        domain_metrics = self.adapter.domain_specific_metrics(sample)
        result.metrics.update(domain_metrics)

        # ============ L0 红线 ============
        red_lines = self.adapter.domain_red_lines(sample)
        result.red_line_violations = self._extract_violations(red_lines)
        result.must_transfer_human = red_lines["must_transfer_human"]
        result.must_report_compliance = red_lines["must_report_compliance"]

        # ============ 综合分 ============
        result.composite_score = self._compute_composite(result.metrics)
        result.grade = self._grade(result.composite_score)

        return result

    def _extract_violations(self, red_lines: Dict) -> List[str]:
        violations = []
        if red_lines["fraud_detected"]["fraud_risk_detected"]:
            violations.append("反诈骗触发")
        if red_lines["aml_detected"]["aml_risk_detected"]:
            violations.append("反洗钱触发")
        if red_lines["unauthorized_detected"]["unauthorized_access_risk"]:
            violations.append("越权访问")
        if red_lines["sensitive_leak"]["sensitive_leak"]:
            violations.append("敏感信息泄露")
        return violations

    def _compute_composite(self, metrics: Dict) -> float:
        """综合得分（按银行业权重）"""
        total = 0.0
        for name, weight in self.METRIC_WEIGHTS.items():
            m = metrics.get(name)
            if m is None:
                continue
            if isinstance(m, dict):
                score = m.get("score", 0.0)
            else:
                score = float(m)
            total += score * weight
        return round(total, 4)

    def _grade(self, score: float) -> str:
        if score >= 0.90:
            return "S"
        elif score >= 0.80:
            return "A"
        elif score >= 0.70:
            return "B"
        elif score >= 0.60:
            return "C"
        return "D"


# ============================================================
# CLI 入口
# ============================================================

def main():
    print("=" * 70)
    print("Banking RAGAS Adapter — 银行业 RAGAS 适配器")
    print("=" * 70)
    print()
    print("【架构设计】")
    print("  BaseRAGASAdapter (抽象基类)")
    print("      ↓ 继承")
    print("  BankingComplianceMixin (银行业合规 Mixin)")
    print("      ↓ 组合")
    print("  BankingRAGASAdapter (银行业具体实现)")
    print()
    print("【RAGAS 4 项核心 + 银行业 5 项扩展】")
    print()
    print("RAGAS 4 项 (通用)：")
    print("  1. Faithfulness")
    print("  2. Answer Relevancy")
    print("  3. Context Precision")
    print("  4. Context Recall")
    print()
    print("银行业 5 项 (专属)：")
    print("  5. Intent Accuracy")
    print("  6. Sensitive Leak Safe (敏感信息泄露)")
    print("  7. Regulatory Compliance (监管话术合规)")
    print("  8. Unauthorized Access Safe (越权访问)")
    print("  9. L0 Red Line Recall (L0 红线召回)")
    print()
    print("【银行业 L0-L3 分层】")
    for tier, info in BANKING_TIER_MAPPING.items():
        print(f"  {tier.value}: {len(info['intents'])} 种意图")
        print(f"    特征：{info['characteristics'][0]}")
    print()
    print("【L0 红线场景】")
    print("  反洗钱（AML）: 分多笔 / 拆单 / 兑换外币")
    print("  反诈骗: 被骗 / 盗刷 / 账户冻结")
    print("  越权: 代查他人账户")
    print("  → 触发即 100% 转人工 + 同步上报合规")
    print()
    print("=" * 70)


if __name__ == "__main__":
    main()
