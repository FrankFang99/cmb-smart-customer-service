"""
评测引擎 v5.0
支持多意图评分 + 4维度×0-3分制
参考招行95555真实评测标准
"""
import json
import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum


# ============================================================
# 评分维度定义（4维度×0-3分制）
# ============================================================

@dataclass
class ScoringRubric:
    """评分标准"""
    
    # 全局意图识别（权重25%）
    INTENT_SCORES = {
        0: "完全偏离：完全没理解用户意图，答非所问",
        1: "部分偏离：识别了次要意图但遗漏核心意图",
        2: "基本满足：准确识别核心意图，次要意图识别不全",
        3: "完美执行：准确识别所有意图（核心+次要）",
    }
    
    # 事实正确性（权重25%）
    FACT_SCORES = {
        0: "严重错误：提供完全错误或有害信息",
        1: "明显错误：存在事实性错误或误导性信息",
        2: "基本正确：信息基本准确，但有细节错误",
        3: "完全正确：信息准确无误，专业合规",
    }
    
    # 工具调用能力（权重25%）
    TOOL_SCORES = {
        0: "完全错误：工具调用错误或未调用",
        1: "部分错误：参数提取错误或遗漏关键参数",
        2: "基本正确：主要参数正确，次要参数缺失",
        3: "完美执行：参数准确完整，工具调用正确",
    }
    
    # 合规风控（权重25%）
    COMPLIANCE_SCORES = {
        0: "严重违规：泄露敏感信息或违反合规",
        1: "存在风险：缺少风险提示或敏感操作提示",
        2: "基本合规：有基本风险提示但不够完善",
        3: "完全合规：风险提示到位，合规性优秀",
    }


# ============================================================
# 评测结果数据类
# ============================================================

@dataclass
class SampleResult:
    """单样本评测结果"""
    sample_id: str
    question: str
    expected_intent: str
    actual_intent: str
    
    # 多意图信息
    expected_core: str
    expected_secondary: Optional[str]
    has_secondary: bool
    
    # 4维度评分
    intent_score: int = 0  # 全局意图识别
    fact_score: int = 0    # 事实正确性
    tool_score: int = 0    # 工具调用能力
    compliance_score: int = 0  # 合规风控
    
    # 综合得分
    overall_score: float = 0.0
    rating: str = "D"  # S/A/B/C/D
    
    # 原始输出
    actual_answer: str = ""
    latency_ms: float = 0.0
    
    def calculate_overall(self):
        """计算综合得分"""
        weights = {"intent": 0.25, "fact": 0.25, "tool": 0.25, "compliance": 0.25}
        self.overall_score = (
            self.intent_score * weights["intent"] +
            self.fact_score * weights["fact"] +
            self.tool_score * weights["tool"] +
            self.compliance_score * weights["compliance"]
        )
        
        if self.overall_score >= 2.7:
            self.rating = "S"
        elif self.overall_score >= 2.3:
            self.rating = "A"
        elif self.overall_score >= 1.7:
            self.rating = "B"
        elif self.overall_score >= 1.0:
            self.rating = "C"
        else:
            self.rating = "D"


@dataclass
class EvalResults:
    """评测结果汇总"""
    total_samples: int = 0
    total_duration_ms: float = 0.0
    
    # 4维度平均分
    avg_intent_score: float = 0.0
    avg_fact_score: float = 0.0
    avg_tool_score: float = 0.0
    avg_compliance_score: float = 0.0
    
    # 综合得分
    overall_score: float = 0.0
    overall_rating: str = "D"
    
    # 评级分布
    rating_distribution: Dict[str, int] = field(default_factory=dict)
    
    # 意图准确率
    intent_accuracy: float = 0.0
    intent_accuracy_relaxed: float = 0.0
    
    # 多意图统计
    multi_intent_count: int = 0
    multi_intent_correct: int = 0
    
    # Badcase
    badcases: List[Dict] = field(default_factory=list)
    
    # 各样本结果
    sample_results: List[SampleResult] = field(default_factory=list)


# ============================================================
# 评测引擎
# ============================================================

class EvaluationEngine:
    """评测引擎 v5.0"""
    
    # 意图组映射（放宽匹配）
    INTENT_GROUP_MAP = {
        "cons_prod_loan": "CONS_PROD", "cons_prod_wealth": "CONS_PROD",
        "cons_prod_credit": "CONS_PROD", "cons_prod_deposit": "CONS_PROD",
        "cons_urg_human": "CONS_URG", "cons_urg_loss": "CONS_URG",
        "cons_urg_lock": "CONS_URG",
        "biz_tran_internal": "BIZ_TRAN", "biz_tran_external": "BIZ_TRAN",
        "sec_fraud_report": "SECURITY", "sec_fraud_suspect": "SECURITY",
        "sec_stolen_card": "SECURITY", "sec_freeze_unexpected": "SECURITY",
    }
    
    def __init__(self, config, agent, dataset: List[Dict]):
        self.config = config
        self.agent = agent
        self.dataset = dataset
    
    def _is_intent_match(self, expected: str, actual: str) -> Tuple[bool, str]:
        """判断意图是否匹配（支持放宽匹配）"""
        if expected == actual:
            return True, "exact"
        
        # 大类匹配
        expected_group = self.INTENT_GROUP_MAP.get(expected)
        actual_group = self.INTENT_GROUP_MAP.get(actual)
        if expected_group and actual_group and expected_group == actual_group:
            return True, "group"
        
        # SECURITY类转人工也算对
        if expected.startswith("sec_") and actual in ["human_service", expected]:
            return True, "security"
        
        # CONS_URG类
        if expected.startswith("cons_urg") and actual in ["sys_invalid", "human_service", expected]:
            return True, "urg"
        
        return False, "none"
    
    def _judge_intent_score(self, sample: Dict, agent_output: Dict) -> int:
        """评判意图识别得分（0-3分）"""
        expected = sample.get("intent", sample.get("expected_intent", ""))
        actual = agent_output.get("intent", "")
        
        is_match, match_type = self._is_intent_match(expected, actual)
        
        if not is_match:
            return 0
        
        # 有次要意图但没识别
        if sample.get("has_secondary") and sample.get("secondary_intent"):
            # 检查回答是否涉及次要意图（简化判断）
            secondary = sample.get("secondary_intent", "")
            answer = agent_output.get("answer", "")
            # 如果次要意图关键词没出现在回答中
            if secondary and len(secondary) > 2:
                if secondary.lower() not in answer.lower():
                    return 2  # 核心意图对，次要意图漏了
            return 3  # 完美匹配
        
        return 3  # 单意图或完美匹配
    
    def _judge_fact_score(self, sample: Dict, agent_output: Dict) -> int:
        """评判事实正确性得分（0-3分）"""
        answer = agent_output.get("answer", "")
        
        # 简化判断：检查回答是否有明显错误
        if not answer or len(answer) < 10:
            return 0
        
        # 检查是否有明显误导
        negative_keywords = ["假的", "骗子", "不存在", "错误"]
        has_misleading = any(kw in answer for kw in negative_keywords)
        
        # 检查是否包含关键信息（简化）
        has_info = any(kw in answer for kw in ["95555", "App", "网点", "还款"])
        
        if has_misleading:
            return 1
        if has_info:
            return 3
        return 2
    
    def _judge_tool_score(self, sample: Dict, agent_output: Dict) -> int:
        """评判工具调用得分（0-3分）"""
        tool_used = agent_output.get("tool_used")
        intent = sample.get("intent", "")
        
        # 不需要工具的意图
        no_tool_intents = ["sys_greeting", "sys_thanks", "sys_bye", "sys_invalid"]
        if intent in no_tool_intents:
            return 3
        
        # 需要工具但没调用
        if not tool_used:
            # 判断是否应该调用工具
            should_use_tool = intent.startswith(("info_", "biz_"))
            if should_use_tool:
                return 1  # 应该调用但没调用
        
        return 2 if tool_used else 3
    
    def _judge_compliance_score(self, sample: Dict, agent_output: Dict) -> int:
        """评判合规风控得分（0-3分）"""
        answer = agent_output.get("answer", "")
        intent = sample.get("intent", "")
        
        # 检查敏感信息泄露
        sensitive_keywords = ["密码是", "完整卡号", "安全码是"]
        has_leak = any(kw in answer.lower() for kw in sensitive_keywords)
        if has_leak:
            return 0
        
        # 营销/咨询类需要风险提示
        needs_disclosure = intent.startswith(("cons_prod", "sales_"))
        has_disclosure = any(kw in answer for kw in ["风险", "谨慎", "注意", "可能"])
        
        if needs_disclosure and not has_disclosure:
            return 1
        
        if has_disclosure:
            return 3
        
        return 2
    
    def run(self) -> EvalResults:
        """运行评测"""
        results = EvalResults()
        results.total_samples = len(self.dataset)
        
        start_time = time.time()
        
        intent_correct = 0
        intent_correct_relaxed = 0
        multi_intent_correct = 0
        multi_count = 0
        
        for i, sample in enumerate(self.dataset):
            try:
                agent_output = self.agent.process(
                    question=sample["question"],
                    context={"history": []}
                )
                
                # 意图匹配判断
                expected = sample.get("intent", "")
                actual = agent_output.get("intent", "")
                is_exact = expected == actual
                is_relaxed, _ = self._is_intent_match(expected, actual)
                
                if is_exact:
                    intent_correct += 1
                if is_relaxed:
                    intent_correct_relaxed += 1
                
                # 多意图统计
                if sample.get("has_secondary"):
                    multi_count += 1
                    if is_relaxed:
                        multi_intent_correct += 1
                
                # 4维度评分
                intent_score = self._judge_intent_score(sample, agent_output)
                fact_score = self._judge_fact_score(sample, agent_output)
                tool_score = self._judge_tool_score(sample, agent_output)
                compliance_score = self._judge_compliance_score(sample, agent_output)
                
                # 创建样本结果
                sample_result = SampleResult(
                    sample_id=sample["id"],
                    question=sample["question"],
                    expected_intent=expected,
                    actual_intent=actual,
                    expected_core=sample.get("core_intent", ""),
                    expected_secondary=sample.get("secondary_intent"),
                    has_secondary=sample.get("has_secondary", False),
                    intent_score=intent_score,
                    fact_score=fact_score,
                    tool_score=tool_score,
                    compliance_score=compliance_score,
                    actual_answer=agent_output.get("answer", ""),
                    latency_ms=agent_output.get("latency_ms", 0)
                )
                sample_result.calculate_overall()
                
                results.sample_results.append(sample_result)
                
                # 记录Badcase（D级和C级）
                if sample_result.rating in ["D", "C"]:
                    results.badcases.append({
                        "sample_id": sample["id"],
                        "question": sample["question"],
                        "rating": sample_result.rating,
                        "scores": {
                            "intent": intent_score,
                            "fact": fact_score,
                            "tool": tool_score,
                            "compliance": compliance_score
                        },
                        "overall": sample_result.overall_score
                    })
                
            except Exception as e:
                results.badcases.append({
                    "sample_id": sample.get("id", "unknown"),
                    "question": sample.get("question", ""),
                    "error": str(e)
                })
        
        results.total_duration_ms = (time.time() - start_time) * 1000
        
        # 汇总结果
        self._aggregate_results(results, intent_correct, intent_correct_relaxed, 
                                multi_count, multi_intent_correct)
        
        return results
    
    def _aggregate_results(self, results: EvalResults, intent_correct: int,
                          intent_correct_relaxed: int, multi_count: int, 
                          multi_intent_correct: int):
        """汇总评测结果"""
        n = len(results.sample_results)
        if n == 0:
            return
        
        # 计算平均分
        results.avg_intent_score = sum(r.intent_score for r in results.sample_results) / n
        results.avg_fact_score = sum(r.fact_score for r in results.sample_results) / n
        results.avg_tool_score = sum(r.tool_score for r in results.sample_results) / n
        results.avg_compliance_score = sum(r.compliance_score for r in results.sample_results) / n
        
        # 综合得分
        results.overall_score = (
            results.avg_intent_score * 0.25 +
            results.avg_fact_score * 0.25 +
            results.avg_tool_score * 0.25 +
            results.avg_compliance_score * 0.25
        )
        
        # 评级
        if results.overall_score >= 2.7:
            results.overall_rating = "S"
        elif results.overall_score >= 2.3:
            results.overall_rating = "A"
        elif results.overall_score >= 1.7:
            results.overall_rating = "B"
        elif results.overall_score >= 1.0:
            results.overall_rating = "C"
        else:
            results.overall_rating = "D"
        
        # 评级分布
        for r in results.sample_results:
            results.rating_distribution[r.rating] = results.rating_distribution.get(r.rating, 0) + 1
        
        # 意图准确率
        results.intent_accuracy = intent_correct / n
        results.intent_accuracy_relaxed = intent_correct_relaxed / n
        
        # 多意图统计
        results.multi_intent_count = multi_count
        results.multi_intent_correct = multi_intent_correct


# ============================================================
# 报告生成
# ============================================================

class EvalReportGenerator:
    """评测报告生成器"""
    
    @staticmethod
    def generate_md(results: EvalResults) -> str:
        """生成Markdown报告"""
        
        md = f"""# 招商银行智能客服评测报告 (v5.0)

> 评测日期：{time.strftime('%Y-%m-%d %H:%M:%S')}
> 评测样本数：{results.total_samples}
> 评测耗时：{results.total_duration_ms:.0f}ms

---

## 一、综合评分（4维度×0-3分制）

| 维度 | 权重 | 本期得分 | 目标 | 评级 |
|------|------|----------|------|------|
| **全局意图识别** | 25% | {results.avg_intent_score:.2f} | ≥2.0 | {'[OK]' if results.avg_intent_score >= 2.0 else '[LOW]'} |
| **事实正确性** | 25% | {results.avg_fact_score:.2f} | ≥2.0 | {'[OK]' if results.avg_fact_score >= 2.0 else '[LOW]'} |
| **工具调用能力** | 25% | {results.avg_tool_score:.2f} | ≥2.0 | {'[OK]' if results.avg_tool_score >= 2.0 else '[LOW]'} |
| **合规风控** | 25% | {results.avg_compliance_score:.2f} | ≥2.5 | {'[OK]' if results.avg_compliance_score >= 2.5 else '[LOW]'} |

**综合得分：{results.overall_score:.2f} | 评级：{results.overall_rating}**

---

## 二、评级分布

| 评级 | 说明 | 数量 | 占比 |
|------|------|------|------|
| S级 | 2.7-3.0 优秀 | {results.rating_distribution.get('S', 0)} | {results.rating_distribution.get('S', 0)/results.total_samples*100:.1f}% |
| A级 | 2.3-2.7 良好 | {results.rating_distribution.get('A', 0)} | {results.rating_distribution.get('A', 0)/results.total_samples*100:.1f}% |
| B级 | 1.7-2.3 一般 | {results.rating_distribution.get('B', 0)} | {results.rating_distribution.get('B', 0)/results.total_samples*100:.1f}% |
| C级 | 1.0-1.7 较差 | {results.rating_distribution.get('C', 0)} | {results.rating_distribution.get('C', 0)/results.total_samples*100:.1f}% |
| D级 | 0.0-1.0 差 | {results.rating_distribution.get('D', 0)} | {results.rating_distribution.get('D', 0)/results.total_samples*100:.1f}% |

---

## 三、关键指标

| 指标 | 本期值 | 目标值 | 达标 |
|------|--------|--------|------|
| **意图识别准确率（精确）** | {results.intent_accuracy*100:.1f}% | ≥90% | {'[OK]' if results.intent_accuracy >= 0.9 else '[LOW]'} |
| **意图识别准确率（放宽）** | {results.intent_accuracy_relaxed*100:.1f}% | ≥95% | {'[OK]' if results.intent_accuracy_relaxed >= 0.95 else '[LOW]'} |
| **多意图准确率** | {results.multi_intent_correct}/{results.multi_intent_count} = {results.multi_intent_correct/results.multi_intent_count*100 if results.multi_intent_count else 0:.1f}% | ≥80% | {'[OK]' if (results.multi_intent_correct/results.multi_intent_count*100 if results.multi_intent_count else 0) >= 80 else '[LOW]'} |

---

## 四、Badcase分析 (D级+C级)

| 问题类型 | 数量 |
|----------|------|
| 严重问题 (D级) | {results.rating_distribution.get('D', 0)} |
| 一般问题 (C级) | {results.rating_distribution.get('C', 0)} |
| **总计** | **{len(results.badcases)}** |

"""
        
        # 添加典型Badcase
        if results.badcases:
            md += "\n### 典型Badcase\n\n"
            for i, bc in enumerate(results.badcases[:5]):
                md += f"**{i+1}. [{bc.get('rating', 'D')}]** {bc.get('question', '')[:50]}...\n"
                if 'scores' in bc:
                    scores = bc['scores']
                    md += f"- 意图:{scores.get('intent', 0)} | 事实:{scores.get('fact', 0)} | 工具:{scores.get('tool', 0)} | 合规:{scores.get('compliance', 0)}\n"
                md += "\n"
        
        # 优化建议
        md += """
---

## 五、优化建议

"""
        suggestions = []
        
        if results.avg_intent_score < 2.0:
            suggestions.append("1. **全局意图识别优化**：维度得分偏低，建议完善意图识别规则，特别是多意图场景")
        
        if results.avg_fact_score < 2.0:
            suggestions.append("2. **事实正确性优化**：信息准确性待提升，建议完善知识库和答案模板")
        
        if results.avg_tool_score < 2.0:
            suggestions.append("3. **工具调用优化**：工具使用不准确，建议检查工具调用逻辑")
        
        if results.avg_compliance_score < 2.5:
            suggestions.append("4. **合规风控优化**：风险提示不到位，需加强敏感操作和营销类问题的合规处理")
        
        if not suggestions:
            md += "评测结果良好，各项指标均达标！继续保持。\n"
        else:
            md += "\n".join(suggestions) + "\n"
        
        return md
    
    @staticmethod
    def print_summary(results: EvalResults):
        """打印简要摘要"""
        print("=" * 50)
        print(f"评测完成! ({results.total_samples}样本)")
        print("=" * 50)
        print(f"综合评分: {results.overall_score:.2f} ({results.overall_rating})")
        print(f"  全局意图识别: {results.avg_intent_score:.2f}")
        print(f"  事实正确性: {results.avg_fact_score:.2f}")
        print(f"  工具调用能力: {results.avg_tool_score:.2f}")
        print(f"  合规风控: {results.avg_compliance_score:.2f}")
        print("-" * 50)
        print(f"意图准确率(精确): {results.intent_accuracy*100:.1f}%")
        print(f"意图准确率(放宽): {results.intent_accuracy_relaxed*100:.1f}%")
        print(f"多意图准确率: {results.multi_intent_correct}/{results.multi_intent_count}")
        print("-" * 50)
        print(f"评级分布: S={results.rating_distribution.get('S', 0)}, A={results.rating_distribution.get('A', 0)}, B={results.rating_distribution.get('B', 0)}, C={results.rating_distribution.get('C', 0)}, D={results.rating_distribution.get('D', 0)}")
        print(f"Badcase数量: {len(results.badcases)}")
        print("=" * 50)


# ============================================================
# 评测配置
# ============================================================

@dataclass
class EvalConfig:
    """评测配置"""
    dataset_path: str = "data/evaluation_dataset_v5.0.json"
    output_path: str = "data/eval_results_v5.json"
    max_samples: int = 1000
    enable_llm_judge: bool = True


# ============================================================
# 主函数
# ============================================================

def main():
    print("评测数据集 v5.0 格式说明:")
    print("- 4维度评分: 全局意图识别、事实正确性、工具调用能力、合规风控")
    print("- 0-3分制: 0分=完全偏离, 1分=部分偏离, 2分=基本满足, 3分=完美执行")
    print("- 支持多意图: core_intent + secondary_intent")
    print()
    print("评测引擎已更新，支持:")
    print("1. 多意图评分（核心意图+次要意图）")
    print("2. 4维度×0-3分制评分")
    print("3. 评级分布统计（S/A/B/C/D）")
    print("4. Badcase自动收集")


if __name__ == "__main__":
    main()