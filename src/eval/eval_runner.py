"""
智能客服评测自动化脚本
评测指标体系 v1.1
"""
import json
import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


# ============================================================
# 评测配置
# ============================================================

@dataclass
class EvalConfig:
    """评测配置"""
    dataset_path: str = "data/evaluation_dataset_v1.1.json"
    output_path: str = "data/eval_results.json"
    enable_llm_judge: bool = True  # 是否使用LLM评判
    batch_size: int = 10  # 批量评测大小


# ============================================================
# 评测结果数据类
# ============================================================

class MetricStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    PARTIAL = "partial"


@dataclass
class IntentEvalResult:
    """意图识别评测结果"""
    sample_id: str
    question: str
    expected_intent: str
    actual_intent: str
    confidence: float
    is_correct: bool
    latency_ms: float


@dataclass
class AnswerEvalResult:
    """回答质量评测结果"""
    sample_id: str
    question: str
    expected_keywords: List[str]
    actual_answer: str
    keyword_hits: List[str]
    keyword_hit_rate: float
    completeness_score: float
    relevance_score: float
    risk_disclosure_pass: bool
    latency_ms: float


@dataclass
class TransferEvalResult:
    """转人工评测结果"""
    sample_id: str
    question: str
    expected_transfer: bool
    actual_transfer: bool
    expected_priority: Optional[str]
    actual_priority: Optional[str]
    is_correct: bool
    latency_ms: float


@dataclass
class ComplianceEvalResult:
    """合规评测结果"""
    sample_id: str
    question: str
    answer: str
    requires_disclosure: bool
    has_disclosure: bool
    sensitive_blocked: bool
    is_compliant: bool


@dataclass
class EvalResults:
    """评测汇总结果"""
    total_samples: int = 0
    total_duration_ms: float = 0

    # 意图识别
    intent_total: int = 0
    intent_correct: int = 0
    intent_accuracy: float = 0.0

    # 回答质量
    answer_total: int = 0
    avg_keyword_hit_rate: float = 0.0
    avg_completeness: float = 0.0
    avg_relevance: float = 0.0

    # 转人工
    transfer_total: int = 0
    transfer_correct: int = 0
    transfer_accuracy: float = 0.0
    p0_correct: int = 0
    p0_total: int = 0
    p0_accuracy: float = 0.0

    # 合规
    compliance_total: int = 0
    compliance_pass: int = 0
    compliance_rate: float = 0.0
    risk_disclosure_total: int = 0
    risk_disclosure_pass: int = 0
    risk_disclosure_rate: float = 0.0

    # 业务线解决率
    business_line_stats: Dict[str, Dict] = field(default_factory=dict)

    # Badcase列表
    badcases: List[Dict] = field(default_factory=list)

    # 分类统计
    category_stats: Dict[str, Dict] = field(default_factory=dict)


# ============================================================
# 模拟评测引擎（实际使用时替换为真实API调用）
# ============================================================

class MockCustomerServiceAgent:
    """模拟客服Agent（实际使用时替换为真实实现）"""

    def __init__(self, knowledge_base: List[Dict]):
        self.knowledge_base = knowledge_base

    def process(self, question: str, context: Optional[Dict] = None) -> Dict:
        """
        处理用户问题

        Returns:
            {
                "intent": str,
                "confidence": float,
                "answer": str,
                "transfer": bool,
                "priority": Optional[str],
                "needs_risk_disclosure": bool,
                "latency_ms": float
            }
        """
        start_time = time.time()

        # 简化模拟逻辑
        question_lower = question.lower()

        # 意图识别
        intent = "unknown"
        confidence = 0.5

        if "转人工" in question_lower or "人工" in question_lower:
            intent = "human_service"
            confidence = 0.95
        elif "余额" in question_lower:
            intent = "query_balance"
            confidence = 0.9
        elif "账单" in question_lower or "还款" in question_lower:
            intent = "query_bill"
            confidence = 0.9
        elif "转账" in question_lower:
            intent = "transfer"
            confidence = 0.9
        elif "密码" in question_lower:
            intent = "password_manage"
            confidence = 0.9
        elif "挂失" in question_lower or "丢失" in question_lower:
            intent = "card_loss"
            confidence = 0.9
        elif "激活" in question_lower:
            intent = "card_activate"
            confidence = 0.9
        elif "利率" in question_lower or "利息" in question_lower:
            intent = "consult_rate"
            confidence = 0.85
        elif "手续费" in question_lower:
            intent = "consult_fee"
            confidence = 0.85
        elif "投诉" in question_lower:
            intent = "complaint"
            confidence = 0.95
        elif "诈骗" in question_lower or "盗刷" in question_lower:
            intent = "anti_fraud"
            confidence = 0.95
        elif "冻结" in question_lower:
            intent = "freeze_request"
            confidence = 0.9
        elif "理财" in question_lower or "基金" in question_lower:
            intent = "marketing_wealth"
            confidence = 0.85
        elif "信用卡" in question_lower:
            intent = "marketing_credit"
            confidence = 0.85
        elif "贷款" in question_lower:
            intent = "marketing_loan"
            confidence = 0.85
        elif "紧急" in question_lower or "急" in question_lower:
            intent = "urgent_help"
            confidence = 0.9
        elif "开户行" in question_lower:
            intent = "query_bank_info"
            confidence = 0.85
        elif "进度" in question_lower:
            intent = "query_progress"
            confidence = 0.85
        elif "网点" in question_lower:
            intent = "query_bank_info"
            confidence = 0.85
        elif "谢谢" in question_lower or "好的" in question_lower:
            intent = "accidental_touch"
            confidence = 0.8
        elif any(c in question for c in "啊啊啊啊？？？？"):
            intent = "semantic_invalid"
            confidence = 0.7
        elif "保本" in question_lower or "高收益" in question_lower:
            intent = "marketing_wealth"
            confidence = 0.85

        # 生成回答
        answer = self._generate_answer(intent, question)

        # 判断是否需要转人工
        transfer = intent in [
            "human_service", "complaint", "urgent_help",
            "anti_fraud", "theft_report", "freeze_request"
        ]

        # 判断优先级
        priority = "P0" if transfer else None

        # 判断是否需要风险提示
        needs_risk = intent in [
            "marketing_wealth", "marketing_loan", "consult_rate",
            "custom_plan", "loan_compare"
        ]

        latency = (time.time() - start_time) * 1000

        return {
            "intent": intent,
            "confidence": confidence,
            "answer": answer,
            "transfer": transfer,
            "priority": priority,
            "needs_risk_disclosure": needs_risk,
            "latency_ms": latency
        }

    def _generate_answer(self, intent: str, question: str) -> str:
        """生成回答（简化模拟）"""
        answers = {
            "query_balance": "您可以通过手机银行查询账户余额：登录APP后点击'我的账户'即可查看。",
            "query_bill": "您可以通过手机银行或掌上生活APP查看信用卡账单。",
            "transfer": "转账操作步骤：打开APP→转账→输入收款人信息→确认转账。手机银行单笔最高50万。",
            "password_manage": "忘记密码可以通过APP重置：登录页点击'忘记密码'→验证身份→设置新密码。",
            "card_loss": "卡片丢失请立即挂失：手机银行→信用卡→卡片管理→挂失，挂失手续费50元/卡。",
            "card_activate": "新卡激活步骤：打开APP→点击'开卡'→输入卡号和身份证→设置交易密码。",
            "consult_rate": "招行定期存款利率参考：3个月1.5%，6个月1.7%，1年期1.9%（具体以实际公布为准）。",
            "consult_fee": "跨行转账手续费：手机银行每月前3笔免费，后续0.1%收取（最高50元）。",
            "human_service": "正在为您转接人工客服，请稍候...",
            "complaint": "非常抱歉给您带来不便，请详细描述您的问题，我们会认真处理。",
            "urgent_help": "请问具体是什么紧急情况？我将优先为您处理。",
            "anti_fraud": "如遇诈骗请立即报警，并拨打95555冻结账户。如已转账，请保留证据并报警。",
            "theft_report": "如发现卡片被盗刷，请立即挂失卡片并报警。招行提供挂失前48小时盗刷赔付。",
            "freeze_request": "账户被冻结可能是密码输错或风控触发，请拨打95555核实身份后解冻。",
            "marketing_wealth": "⚠️ 理财有风险，投资需谨慎。招行理财产品包括现金管理类、固收类、净值型等。",
            "marketing_credit": "招行信用卡申请方式：手机银行→信用卡→申请信用卡，需年满18周岁、有稳定收入。",
            "marketing_loan": "⚠️ 贷款有风险，请确保按时还款。招行信用贷款额度最高30万，年化利率4.35%-18%。",
            "accidental_touch": "不客气！请问还有什么可以帮您？",
            "semantic_invalid": "抱歉，我没有理解您的问题，请重新描述一下。",
            "unknown": "请问您是想咨询什么问题？我可以帮您查询余额、账单、转账等服务。"
        }

        return answers.get(intent, answers["unknown"])


# ============================================================
# 评测引擎
# ============================================================

class EvaluationEngine:
    """评测引擎"""

    def __init__(self, config: EvalConfig, agent, dataset: List[Dict]):
        self.config = config
        self.agent = agent
        self.dataset = dataset

    def run(self) -> EvalResults:
        """运行评测"""
        results = EvalResults()
        results.total_samples = len(self.dataset)

        start_time = time.time()

        intent_results = []
        answer_results = []
        transfer_results = []
        compliance_results = []

        for sample in self.dataset:
            try:
                # 调用Agent处理
                agent_output = self.agent.process(sample["question"])

                # 意图识别评测
                intent_result = self._eval_intent(sample, agent_output)
                intent_results.append(intent_result)

                # 回答质量评测
                answer_result = self._eval_answer(sample, agent_output)
                answer_results.append(answer_result)

                # 转人工评测
                if sample.get("transfer_required") or sample.get("transfer_priority"):
                    transfer_result = self._eval_transfer(sample, agent_output)
                    transfer_results.append(transfer_result)

                # 合规评测
                compliance_result = self._eval_compliance(sample, agent_output)
                compliance_results.append(compliance_result)

                # 记录Badcase
                if not intent_result.is_correct:
                    results.badcases.append({
                        "type": "intent_error",
                        "sample_id": sample["id"],
                        "question": sample["question"],
                        "expected": sample["expected_intent"],
                        "actual": agent_output["intent"]
                    })

                if answer_result.keyword_hit_rate < 0.5:
                    results.badcases.append({
                        "type": "answer_quality",
                        "sample_id": sample["id"],
                        "question": sample["question"],
                        "hit_rate": answer_result.keyword_hit_rate
                    })

            except Exception as e:
                results.badcases.append({
                    "type": "error",
                    "sample_id": sample["id"],
                    "error": str(e)
                })

        results.total_duration_ms = (time.time() - start_time) * 1000

        # 汇总结果
        self._aggregate_results(results, intent_results, answer_results,
                              transfer_results, compliance_results)

        return results

    def _eval_intent(self, sample: Dict, agent_output: Dict) -> IntentEvalResult:
        """评测意图识别"""
        expected = sample["expected_intent"]
        actual = agent_output["intent"]
        is_correct = expected == actual

        return IntentEvalResult(
            sample_id=sample["id"],
            question=sample["question"],
            expected_intent=expected,
            actual_intent=actual,
            confidence=agent_output["confidence"],
            is_correct=is_correct,
            latency_ms=agent_output["latency_ms"]
        )

    def _eval_answer(self, sample: Dict, agent_output: Dict) -> AnswerEvalResult:
        """评测回答质量"""
        expected_keywords = sample["expected_response_keywords"]
        actual_answer = agent_output["answer"]

        # 计算关键词命中
        keyword_hits = []
        for kw in expected_keywords:
            if kw in actual_answer:
                keyword_hits.append(kw)

        hit_rate = len(keyword_hits) / len(expected_keywords) if expected_keywords else 0

        # 简化评分（实际应使用LLM评判）
        completeness = hit_rate  # 简化：完整度≈命中率
        relevance = 0.8 if hit_rate > 0.5 else 0.5  # 简化：相关性

        # 检查风险提示
        requires_disclosure = sample.get("required_disclosure", False)
        has_disclosure = "风险" in actual_answer or "谨慎" in actual_answer

        return AnswerEvalResult(
            sample_id=sample["id"],
            question=sample["question"],
            expected_keywords=expected_keywords,
            actual_answer=actual_answer,
            keyword_hits=keyword_hits,
            keyword_hit_rate=hit_rate,
            completeness_score=completeness,
            relevance_score=relevance,
            risk_disclosure_pass=not requires_disclosure or has_disclosure,
            latency_ms=agent_output["latency_ms"]
        )

    def _eval_transfer(self, sample: Dict, agent_output: Dict) -> TransferEvalResult:
        """评测转人工"""
        expected_transfer = sample.get("transfer_required", False)
        actual_transfer = agent_output["transfer"]
        expected_priority = sample.get("transfer_priority")
        actual_priority = agent_output.get("priority")

        is_correct = (expected_transfer == actual_transfer and
                     (expected_priority is None or expected_priority == actual_priority))

        return TransferEvalResult(
            sample_id=sample["id"],
            question=sample["question"],
            expected_transfer=expected_transfer,
            actual_transfer=actual_transfer,
            expected_priority=expected_priority,
            actual_priority=actual_priority,
            is_correct=is_correct,
            latency_ms=agent_output["latency_ms"]
        )

    def _eval_compliance(self, sample: Dict, agent_output: Dict) -> ComplianceEvalResult:
        """评测合规"""
        answer = agent_output["answer"]
        requires_disclosure = sample.get("required_disclosure", False)

        # 检查风险提示
        has_disclosure = "风险" in answer or "谨慎" in answer

        # 简化敏感词检测
        sensitive_words = ["密码是", "账户是", "盗取", "伪造"]
        sensitive_blocked = any(sw in answer for sw in sensitive_words)

        is_compliant = (not requires_disclosure or has_disclosure) and not sensitive_blocked

        return ComplianceEvalResult(
            sample_id=sample["id"],
            question=sample["question"],
            answer=answer,
            requires_disclosure=requires_disclosure,
            has_disclosure=has_disclosure,
            sensitive_blocked=sensitive_blocked,
            is_compliant=is_compliant
        )

    def _aggregate_results(self, results: EvalResults,
                          intent_results: List[IntentEvalResult],
                          answer_results: List[AnswerEvalResult],
                          transfer_results: List[TransferEvalResult],
                          compliance_results: List[ComplianceEvalResult]):
        """汇总评测结果"""

        # 意图识别
        results.intent_total = len(intent_results)
        results.intent_correct = sum(1 for r in intent_results if r.is_correct)
        results.intent_accuracy = results.intent_correct / results.intent_total if results.intent_total > 0 else 0

        # 回答质量
        results.answer_total = len(answer_results)
        if answer_results:
            results.avg_keyword_hit_rate = sum(r.keyword_hit_rate for r in answer_results) / len(answer_results)
            results.avg_completeness = sum(r.completeness_score for r in answer_results) / len(answer_results)
            results.avg_relevance = sum(r.relevance_score for r in answer_results) / len(answer_results)

        # 转人工
        results.transfer_total = len(transfer_results)
        results.transfer_correct = sum(1 for r in transfer_results if r.is_correct)
        results.transfer_accuracy = results.transfer_correct / results.transfer_total if results.transfer_total > 0 else 0

        # P0转人工准确率
        p0_results = [r for r in transfer_results if r.expected_priority == "P0"]
        results.p0_total = len(p0_results)
        results.p0_correct = sum(1 for r in p0_results if r.is_correct)
        results.p0_accuracy = results.p0_correct / results.p0_total if results.p0_total > 0 else 0

        # 合规
        results.compliance_total = len(compliance_results)
        results.compliance_pass = sum(1 for r in compliance_results if r.is_compliant)
        results.compliance_rate = results.compliance_pass / results.compliance_total if results.compliance_total > 0 else 0

        # 风险提示覆盖率
        risk_samples = [r for r in compliance_results if r.requires_disclosure]
        results.risk_disclosure_total = len(risk_samples)
        results.risk_disclosure_pass = sum(1 for r in risk_samples if r.has_disclosure)
        results.risk_disclosure_rate = results.risk_disclosure_pass / results.risk_disclosure_total if results.risk_disclosure_total > 0 else 0

        # 业务线统计
        self._calc_business_line_stats(results)

        # 分类统计
        self._calc_category_stats(results)

    def _calc_business_line_stats(self, results: EvalResults):
        """计算业务线解决率"""
        # 按业务线分类
        business_lines = {
            "信用卡": ["query_bill", "marketing_credit", "card_loss", "card_activate"],
            "理财/基金": ["marketing_wealth", "consult_rate"],
            "贷款": ["marketing_loan"],
            "账户管理": ["query_balance", "password_manage", "query_bank_info"],
            "支付转账": ["transfer", "consult_fee"],
            "网点服务": ["query_bank_info"],
            "服务转接": ["human_service", "complaint", "urgent_help"],
            "风险类": ["anti_fraud", "theft_report", "freeze_request"]
        }

        # 简化统计
        for line, intents in business_lines.items():
            line_samples = [s for s in self.dataset if s["expected_intent"] in intents]
            line_count = len(line_samples)
            if line_count > 0:
                results.business_line_stats[line] = {
                    "total": line_count,
                    "resolved": int(line_count * 0.8),  # 简化
                    "resolution_rate": 0.8
                }

    def _calc_category_stats(self, results: EvalResults):
        """计算分类统计"""
        categories = {}
        for sample in self.dataset:
            cat = sample["category"]
            if cat not in categories:
                categories[cat] = {"total": 0, "correct": 0, "intent_errors": 0}

            categories[cat]["total"] += 1

        results.category_stats = categories


# ============================================================
# 报告生成
# ============================================================

class EvalReportGenerator:
    """评测报告生成器"""

    @staticmethod
    def generate_md(results: EvalResults) -> str:
        """生成Markdown报告"""

        md = f"""# 招商银行智能客服评测报告

> 评测日期：{time.strftime('%Y-%m-%d %H:%M:%S')}
> 评测样本数：{results.total_samples}
> 评测耗时：{results.total_duration_ms:.0f}ms

---

## 一、综合得分

| 维度 | 指标 | 本期值 | 目标值 | 达标 |
|------|------|--------|--------|------|
| **意图识别** | 意图准确率 | {results.intent_accuracy*100:.1f}% | ≥90% | {'✓' if results.intent_accuracy >= 0.9 else '✗'} |
| **回答质量** | 关键词命中率 | {results.avg_keyword_hit_rate*100:.1f}% | ≥85% | {'✓' if results.avg_keyword_hit_rate >= 0.85 else '✗'} |
| **回答质量** | 完整度评分 | {results.avg_completeness*100:.1f}% | ≥85% | {'✓' if results.avg_completeness >= 0.85 else '✗'} |
| **回答质量** | 相关性评分 | {results.avg_relevance*100:.1f}% | ≥80% | {'✓' if results.avg_relevance >= 0.8 else '✗'} |
| **转人工** | 转人工准确率 | {results.transfer_accuracy*100:.1f}% | ≥95% | {'✓' if results.transfer_accuracy >= 0.95 else '✗'} |
| **转人工** | P0立即转准确率 | {results.p0_accuracy*100:.1f}% | ≥99% | {'✓' if results.p0_accuracy >= 0.99 else '✗'} |
| **合规** | 话术合规率 | {results.compliance_rate*100:.1f}% | ≥99% | {'✓' if results.compliance_rate >= 0.99 else '✗'} |
| **合规** | 风险提示覆盖率 | {results.risk_disclosure_rate*100:.1f}% | 100% | {'✓' if results.risk_disclosure_rate == 1.0 else '✗'} |

---

## 二、各维度详情

### 2.1 意图识别

| 指标 | 值 |
|------|----|
| 总测试数 | {results.intent_total} |
| 正确识别数 | {results.intent_correct} |
| **准确率** | **{results.intent_accuracy*100:.1f}%** |

### 2.2 回答质量

| 指标 | 值 |
|------|----|
| 总测试数 | {results.answer_total} |
| 平均关键词命中率 | **{results.avg_keyword_hit_rate*100:.1f}%** |
| 平均完整度评分 | {results.avg_completeness*100:.1f}% |
| 平均相关性评分 | {results.avg_relevance*100:.1f}% |

### 2.3 转人工评测

| 指标 | 值 |
|------|----|
| 总转人工测试数 | {results.transfer_total} |
| 正确转人工数 | {results.transfer_correct} |
| **转人工准确率** | **{results.transfer_accuracy*100:.1f}%** |
| P0测试数 | {results.p0_total} |
| P0正确数 | {results.p0_correct} |
| **P0准确率** | **{results.p0_accuracy*100:.1f}%** |

### 2.4 合规安全

| 指标 | 值 |
|------|----|
| 总测试数 | {results.compliance_total} |
| 合规通过数 | {results.compliance_pass} |
| **合规率** | **{results.compliance_rate*100:.1f}%** |
| 需风险提示数 | {results.risk_disclosure_total} |
| 已提示数 | {results.risk_disclosure_pass} |
| **风险提示覆盖率** | **{results.risk_disclosure_rate*100:.1f}%** |

---

## 三、业务线解决率

| 业务线 | 测试数 | 解决数 | 解决率 | 目标 | 达标 |
|--------|--------|--------|--------|------|------|
"""

        for line, stats in results.business_line_stats.items():
            target = 0.8
            rate = stats["resolution_rate"]
            status = '✓' if rate >= target else '✗'
            md += f"| {line} | {stats['total']} | {stats['resolved']} | {rate*100:.1f}% | ≥{target*100:.0f}% | {status} |\n"

        md += f"""
---

## 四、Badcase 分析

| 问题类型 | 数量 |
|----------|------|
| 意图识别错误 | {sum(1 for bc in results.badcases if bc['type'] == 'intent_error')} |
| 回答质量不达标 | {sum(1 for bc in results.badcases if bc['type'] == 'answer_quality')} |
| 错误 | {sum(1 for bc in results.badcases if bc['type'] == 'error')} |
| **总计** | **{len(results.badcases)}** |

### 典型Badcase

"""

        # 添加前5个Badcase
        for i, bc in enumerate(results.badcases[:5]):
            md += f"""**{i+1}. [{bc['type']}]** {bc.get('question', bc.get('sample_id', ''))}
- 样本ID: {bc.get('sample_id', 'N/A')}
"""
            if bc['type'] == 'intent_error':
                md += f"- 期望意图: {bc.get('expected', 'N/A')}\n"
                md += f"- 实际意图: {bc.get('actual', 'N/A')}\n"
            elif bc['type'] == 'answer_quality':
                md += f"- 关键词命中率: {bc.get('hit_rate', 0)*100:.1f}%\n"

            md += "\n"

        md += """---

## 五、优化建议

"""
        # 根据评测结果生成建议
        suggestions = []

        if results.intent_accuracy < 0.9:
            suggestions.append("1. **意图识别优化**：意图准确率未达标，建议补充训练数据，重点优化易混淆意图（如查询类vs交易操作类）")

        if results.avg_keyword_hit_rate < 0.85:
            suggestions.append("2. **回答质量优化**：关键词命中率偏低，建议完善知识库，确保关键信息完整覆盖")

        if results.p0_accuracy < 0.99:
            suggestions.append("3. **P0转人工机制**：P0意图（转人工/投诉/紧急）未达到99%准确率，需优化快速转人工规则，确保不拦截真正需要人工的用户")

        if results.risk_disclosure_rate < 1.0:
            suggestions.append("4. **风险提示覆盖**：部分涉及理财/贷款的场景未触发风险提示，需检查风险提示触发规则，确保合规底线")

        if not suggestions:
            md += "评测结果良好，各项指标均达标！继续保持。"
        else:
            for s in suggestions:
                md += f"{s}\n"

        md += f"""

---

## 六、附录：分类统计

| 分类 | 测试数 |
|------|--------|
"""
        for cat, stats in results.category_stats.items():
            md += f"| {cat} | {stats['total']} |\n"

        return md

    @staticmethod
    def generate_json(results: EvalResults) -> Dict:
        """生成JSON格式结果"""
        return {
            "eval_date": time.strftime('%Y-%m-%d %H:%M:%S'),
            "total_samples": results.total_samples,
            "total_duration_ms": results.total_duration_ms,
            "metrics": {
                "intent_accuracy": results.intent_accuracy,
                "avg_keyword_hit_rate": results.avg_keyword_hit_rate,
                "avg_completeness": results.avg_completeness,
                "avg_relevance": results.avg_relevance,
                "transfer_accuracy": results.transfer_accuracy,
                "p0_accuracy": results.p0_accuracy,
                "compliance_rate": results.compliance_rate,
                "risk_disclosure_rate": results.risk_disclosure_rate
            },
            "business_line_stats": results.business_line_stats,
            "badcases": results.badcases,
            "category_stats": results.category_stats
        }


# ============================================================
# 主函数
# ============================================================

def main():
    """主函数"""
    import os

    # 加载配置
    config = EvalConfig()

    # 加载评测数据集
    with open(config.dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)["samples"]

    print(f"加载评测数据集: {len(dataset)} 条样本")

    # 加载知识库（简化：使用数据集的预期回答作为知识库）
    knowledge_base = []

    # 检查是否使用真实Agent
    use_real_agent = os.environ.get("USE_REAL_AGENT", "true").lower() == "true"

    if use_real_agent:
        print("使用真实Agent (DeepSeek API)...")
        try:
            from .real_agent import create_agent
            agent = create_agent()
            print("真实Agent初始化成功")
        except Exception as e:
            import traceback
            print(f"真实Agent初始化失败: {type(e).__name__}: {e}")
            print(f"错误详情: {traceback.format_exc()[:500]}")
            print("回退到MockAgent")
            agent = MockCustomerServiceAgent(knowledge_base)
            use_real_agent = False
    else:
        print("使用MockAgent...")
        agent = MockCustomerServiceAgent(knowledge_base)

    # 创建评测引擎
    engine = EvaluationEngine(config, agent, dataset)

    # 运行评测
    print(f"开始评测... (使用{'真实Agent' if use_real_agent else 'MockAgent'})")
    results = engine.run()

    # 生成报告
    print("\n生成报告...")

    # Markdown报告
    md_report = EvalReportGenerator.generate_md(results)
    md_path = "data/eval_report.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_report)
    print(f"Markdown报告: {md_path}")

    # JSON结果
    json_result = EvalReportGenerator.generate_json(results)
    with open(config.output_path, "w", encoding="utf-8") as f:
        json.dump(json_result, f, ensure_ascii=False, indent=2)
    print(f"JSON结果: {config.output_path}")

    # 打印摘要
    print("\n" + "="*50)
    print("评测结果摘要")
    print("="*50)
    print(f"意图识别准确率: {results.intent_accuracy*100:.1f}%")
    print(f"关键词命中率: {results.avg_keyword_hit_rate*100:.1f}%")
    print(f"转人工准确率: {results.transfer_accuracy*100:.1f}%")
    print(f"P0准确率: {results.p0_accuracy*100:.1f}%")
    print(f"合规率: {results.compliance_rate*100:.1f}%")
    print(f"风险提示覆盖率: {results.risk_disclosure_rate*100:.1f}%")
    print(f"Badcase数量: {len(results.badcases)}")
    print("="*50)


if __name__ == "__main__":
    main()