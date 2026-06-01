"""
业务指标体系 — 对齐客服中心业界四象限
========================================

参考：
- 行业标准：CSAT / FCR / 转人工率 / 响应时长（参考：客服中心绩效管理白皮书）
- 银行场景：95555 客服运营 KPI、转人工分层策略
- 招行实践：智能客服 + 人工坐席协同指标体系

为什么需要这层指标？
- 评测指标（RAGAS 7 项）反映"AI 答得对不对"
- 业务指标（CSAT/FCR 等）反映"用户买不买账、能不能省钱"
- 二者结合才是完整的 AI 产品运营视角

核心思想：
1. 四象限联动 — 不看单一指标，CSAT 高 + FCR 低 = "机械解决但态度差"
2. 分层评估 — L1 简单问题 / L2 中等 / L3 复杂 单独算转人工率
3. 钱效映射 — 单次解决成本 vs 节省人力成本

作者：方逸之
更新时间：2026-06-01
"""

import json
import time
import statistics
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum
from collections import defaultdict


# ============================================================
# 业务指标定义
# ============================================================

class MetricCategory(str, Enum):
    """指标分类（对齐业界四象限）"""
    EFFICIENCY = "efficiency"      # 效率层
    QUALITY = "quality"            # 质量层
    EXPERIENCE = "experience"      # 体验层
    COST = "cost"                  # 成本层


@dataclass
class BusinessMetricDef:
    """业务指标定义"""
    CSAT = {
        "name": "CSAT（客户满意度）",
        "category": MetricCategory.EXPERIENCE.value,
        "definition": "用户对本次服务的满意度评分（1-5 分）",
        "industry_benchmark": "≥ 4.0 为合格，≥ 4.3 为优秀",
        "computation": "用户主动评分的算术平均 / 综合得分线性映射",
        "tier_target": {"L1": 4.5, "L2": 4.2, "L3": 4.0},
    }
    FCR = {
        "name": "FCR（首次解决率）",
        "category": MetricCategory.QUALITY.value,
        "definition": "用户问题在第一次接触（不转人工）就被解决的比例",
        "industry_benchmark": "≥ 70% 为合格，每提升 1% CSAT +3-5%",
        "computation": "一次解决的会话数 / 总会话数",
        "tier_target": {"L1": 90, "L2": 75, "L3": 50},
    }
    TRANSFER_RATE = {
        "name": "转人工率",
        "category": MetricCategory.QUALITY.value,
        "definition": "用户主动要求转人工或被判定为需要转人工的比例",
        "industry_benchmark": "不是越低越好，关键看分层",
        "computation": "转人工会话数 / 总会话数",
        "tier_target": {"L1": 5, "L2": 15, "L3": 50},
    }
    RESPONSE_TIME = {
        "name": "响应时长",
        "category": MetricCategory.EFFICIENCY.value,
        "definition": "从用户发消息到 AI 给回复的时长（秒）",
        "industry_benchmark": "简单查询 < 1s，DB 查询 < 3s",
        "computation": "P50 / P95 / P99 分位数",
        "tier_target": {"L1": 1.0, "L2": 2.5, "L3": 5.0},
    }
    NPS = {
        "name": "NPS（净推荐值）",
        "category": MetricCategory.EXPERIENCE.value,
        "definition": "推荐者（9-10分）比例 - 贬损者（0-6分）比例",
        "industry_benchmark": "金融行业 ≥ 30 为合格",
        "computation": "(promoter - detractor) / total * 100",
        "tier_target": {"L1": 50, "L2": 35, "L3": 20},
    }
    COST_PER_CASE = {
        "name": "单次服务成本",
        "category": MetricCategory.COST.value,
        "definition": "处理一次客服会话的综合成本（人力 + 算力 + 知识库维护）",
        "industry_benchmark": "AI 客服 < 1 元，人工客服 5-15 元",
        "computation": "LLM token 成本 + 知识库运维摊销 + 边际人力",
        "tier_target": {"L1": 0.5, "L2": 1.0, "L3": 3.0},
    }
    UPLIFT = {
        "name": "Uplift（增量价值）",
        "category": MetricCategory.COST.value,
        "definition": "AI 客服相对纯人工的边际收益（钱效）",
        "industry_benchmark": "ROI > 300% 视为成功",
        "computation": "(节省人力成本 - AI 投入) / AI 投入",
        "tier_target": {"L1": 800, "L2": 500, "L3": 200},
    }


# ============================================================
# 业务问题分层（招行 95555 实战）
# ============================================================

class ProblemTier(str, Enum):
    """问题复杂度分层"""
    L1_SIMPLE = "L1"  # 简单：FAQ 类，单轮可答
    L2_MEDIUM = "L2"  # 中等：需要查数据/调用工具
    L3_COMPLEX = "L3"  # 复杂：投诉/纠纷/诈骗/合规


# L1 / L2 / L3 的意图映射（参考招行真实数据）
TIER_MAPPING = {
    # L1 简单问题（占 60%，AI 应 90%+ 解决）
    ProblemTier.L1_SIMPLE: [
        "card_bill_query",       # 账单查询
        "card_balance_query",    # 余额查询
        "card_limit_query",      # 额度查询
        "card_points_query",     # 积分查询
        "product_consult",       # 产品咨询
        "branch_query",          # 网点查询
        "rate_query",            # 利率查询
        "business_hours",        # 营业时间
    ],
    # L2 中等问题（占 30%，AI 应 70%+ 解决）
    ProblemTier.L2_MEDIUM: [
        "transfer_guide",        # 转账指引
        "card_activate",         # 卡片激活
        "password_reset",        # 密码重置
        "limit_adjust",          # 额度调整
        "bill_installment",      # 账单分期
        "card_replace",          # 补卡
        "statement_request",     # 对账单申请
    ],
    # L3 复杂问题（占 10%，AI 应 50%+ 识别并转人工）
    ProblemTier.L3_COMPLEX: [
        "fraud_report",          # 诈骗报案
        "account_freeze",        # 账户冻结
        "complaint",             # 投诉
        "dispute",               # 交易争议
        "loan_issue",            # 贷款问题
        "tax_compliance",        # 合规税务
        "legal_affairs",         # 法律事务
    ],
}


# ============================================================
# 业务会话数据类
# ============================================================

@dataclass
class BusinessSession:
    """单次业务会话记录"""
    session_id: str
    user_id: str
    intent: str
    tier: str  # L1 / L2 / L3
    start_ts: float
    end_ts: Optional[float] = None
    first_response_ts: Optional[float] = None

    # AI 表现
    ai_resolved: bool = False
    transferred_to_human: bool = False

    # 用户反馈
    csat_score: Optional[int] = None  # 1-5
    nps_score: Optional[int] = None   # 0-10
    is_promoter: bool = False
    is_detractor: bool = False

    # 成本数据
    llm_tokens: int = 0
    llm_cost: float = 0.0
    knowledge_base_hits: int = 0
    human_assist_minutes: float = 0.0  # 人工辅助时长（分钟）

    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BusinessKPIReport:
    """业务 KPI 报告"""
    total_sessions: int
    by_tier: Dict[str, Dict[str, float]] = field(default_factory=dict)
    overall: Dict[str, float] = field(default_factory=dict)
    quadrant_analysis: List[Dict[str, Any]] = field(default_factory=list)
    money_impact: Dict[str, float] = field(default_factory=dict)
    period: str = ""
    generated_at: str = ""

    def to_dict(self):
        return {
            "period": self.period,
            "total_sessions": self.total_sessions,
            "overall": self.overall,
            "by_tier": self.by_tier,
            "quadrant_analysis": self.quadrant_analysis,
            "money_impact": self.money_impact,
            "generated_at": self.generated_at,
        }


# ============================================================
# 业务指标计算器
# ============================================================

class BusinessMetricsCalculator:
    """业务指标计算器 — 对齐业界四象限 + 钱效映射"""

    def __init__(
        self,
        human_cost_per_hour: float = 50.0,        # 人工坐席时薪（元）
        avg_human_handle_min: float = 5.0,         # 人工平均处理时长（分钟）
        llm_cost_per_1k_tokens: float = 0.001,     # LLM 单价（元/1k tokens）
        knowledge_base_maintenance_monthly: float = 5000.0,  # 知识库月维护成本
    ):
        self.human_cost = human_cost_per_hour
        self.human_handle_min = avg_human_handle_min
        self.llm_cost = llm_cost_per_1k_tokens
        self.kb_monthly_cost = knowledge_base_maintenance_monthly

    def compute_kpis(
        self,
        sessions: List[BusinessSession],
        period: str = "monthly"
    ) -> BusinessKPIReport:
        """计算业务 KPI 报告"""
        report = BusinessKPIReport(
            total_sessions=len(sessions),
            period=period,
            generated_at=time.strftime("%Y-%m-%d %H:%M:%S"),
        )

        # ============ 1. 分层聚合 ============
        by_tier = defaultdict(list)
        for s in sessions:
            by_tier[s.tier].append(s)

        for tier, tier_sessions in by_tier.items():
            report.by_tier[tier] = self._compute_tier_metrics(tier_sessions)

        # ============ 2. 全局指标 ============
        report.overall = self._compute_overall_metrics(sessions)

        # ============ 3. 四象限联动分析 ============
        report.quadrant_analysis = self._quadrant_analysis(report.overall)

        # ============ 4. 钱效计算 ============
        report.money_impact = self._compute_money_impact(sessions)

        return report

    def _compute_tier_metrics(self, sessions: List[BusinessSession]) -> Dict[str, float]:
        """单层指标"""
        n = len(sessions)
        if n == 0:
            return {}

        # FCR
        fcr = sum(1 for s in sessions if s.ai_resolved) / n
        # 转人工率
        transfer_rate = sum(1 for s in sessions if s.transferred_to_human) / n
        # CSAT 平均
        csat_scores = [s.csat_score for s in sessions if s.csat_score is not None]
        csat_avg = statistics.mean(csat_scores) if csat_scores else 0.0
        # NPS
        promoters = sum(1 for s in sessions if s.is_promoter)
        detractors = sum(1 for s in sessions if s.is_detractor)
        nps = ((promoters - detractors) / n * 100) if n > 0 else 0.0
        # 响应时长
        response_times = [
            (s.first_response_ts - s.start_ts) for s in sessions
            if s.first_response_ts is not None
        ]
        p50_rt = statistics.median(response_times) if response_times else 0.0
        response_times_sorted = sorted(response_times) if response_times else [0]
        p95_idx = int(n * 0.95)
        p95_rt = response_times_sorted[min(p95_idx, n - 1)]
        # 单次成本
        total_cost = sum(self._session_cost(s) for s in sessions)
        avg_cost = total_cost / n

        return {
            "session_count": n,
            "FCR": round(fcr * 100, 2),          # 百分比
            "transfer_rate": round(transfer_rate * 100, 2),
            "CSAT": round(csat_avg, 2),
            "NPS": round(nps, 2),
            "P50_response_sec": round(p50_rt, 2),
            "P95_response_sec": round(p95_rt, 2),
            "avg_cost_per_case": round(avg_cost, 4),
        }

    def _compute_overall_metrics(self, sessions: List[BusinessSession]) -> Dict[str, float]:
        """全局指标"""
        n = len(sessions)
        if n == 0:
            return {}

        fcr = sum(1 for s in sessions if s.ai_resolved) / n
        transfer_rate = sum(1 for s in sessions if s.transferred_to_human) / n
        csat_scores = [s.csat_score for s in sessions if s.csat_score is not None]
        csat_avg = statistics.mean(csat_scores) if csat_scores else 0.0
        promoters = sum(1 for s in sessions if s.is_promoter)
        detractors = sum(1 for s in sessions if s.is_detractor)
        nps = ((promoters - detractors) / n * 100) if n > 0 else 0.0
        # 响应时长
        response_times = [
            (s.first_response_ts - s.start_ts) for s in sessions
            if s.first_response_ts is not None
        ]
        p50_rt = statistics.median(response_times) if response_times else 0.0
        p95_rt = sorted(response_times)[int(len(response_times) * 0.95)] if response_times else 0.0
        # 总成本
        total_cost = sum(self._session_cost(s) for s in sessions)
        avg_cost = total_cost / n

        return {
            "session_count": n,
            "FCR": round(fcr * 100, 2),
            "transfer_rate": round(transfer_rate * 100, 2),
            "CSAT": round(csat_avg, 2),
            "NPS": round(nps, 2),
            "P50_response_sec": round(p50_rt, 2),
            "P95_response_sec": round(p95_rt, 2),
            "avg_cost_per_case": round(avg_cost, 4),
            "total_llm_cost": round(sum(s.llm_cost for s in sessions), 2),
        }

    def _quadrant_analysis(self, overall: Dict[str, float]) -> List[Dict[str, Any]]:
        """
        四象限联动分析（业界方法论）
        - 模式A：响应快 + 转人工高 = "回复快但没用"
        - 模式B：FCR 高 + CSAT 低 = "机械解决但态度差"
        - 模式C：转人工低 + CSAT 低 = "AI 在硬撑"
        - 模式D：响应慢 + FCR 高 = "慢但靠谱"
        """
        if not overall:
            return []

        fcr = overall.get("FCR", 0)
        transfer = overall.get("transfer_rate", 0)
        csat = overall.get("CSAT", 0)
        p50_rt = overall.get("P50_response_sec", 0)

        findings = []

        # 模式A：响应快 + 转人工率高
        if p50_rt < 1.0 and transfer > 20:
            findings.append({
                "pattern": "A",
                "name": "回复快但没用",
                "diagnosis": "智能体秒回一堆废话，用户发现解决不了问题，还是得转人工",
                "root_cause": ["知识库覆盖不够", "意图识别不准", "答案模板化"],
                "action": ["先优化答案质量", "扩充 FAQ 知识库", "调整意图分类"],
                "severity": "high",
            })

        # 模式B：FCR 高 + CSAT 低
        if fcr > 70 and csat < 4.0 and csat > 0:
            findings.append({
                "pattern": "B",
                "name": "机械解决但态度差",
                "diagnosis": "智能体像个复读机，最后给了正确答案但过程没共情",
                "root_cause": ["话术生硬", "缺少情感识别", "流程缺乏缓冲语"],
                "action": ["优化话术", "增加缓冲语", "情感识别+共情表达"],
                "severity": "medium",
            })

        # 模式C：转人工低 + CSAT 低（危险信号）
        if transfer < 5 and csat < 3.5 and csat > 0:
            findings.append({
                "pattern": "C",
                "name": "AI 在硬撑（危险）",
                "diagnosis": "复杂问题被 AI 硬接，用户流失风险高",
                "root_cause": ["转人工阈值过高", "AI 假装没听懂"],
                "action": ["降低转人工阈值", "主动弹转人工选项", "置信度 < 60% 即转人工"],
                "severity": "critical",
            })

        # 模式D：响应慢 + FCR 高
        if p50_rt > 3.0 and fcr > 70:
            findings.append({
                "pattern": "D",
                "name": "慢但靠谱",
                "diagnosis": "响应偏慢但用户愿意等",
                "root_cause": ["检索链路长", "LLM 推理慢"],
                "action": ["加流式输出", "压缩 prompt", "缓存高频问题"],
                "severity": "low",
            })

        return findings

    def _compute_money_impact(self, sessions: List[BusinessSession]) -> Dict[str, float]:
        """
        钱效计算（Uplift Model 思路）
        节省 = AI 替代的人工成本 - AI 自身成本
        """
        n = len(sessions)
        if n == 0:
            return {}

        # AI 解决的部分（不被转人工）
        ai_resolved_count = sum(1 for s in sessions if s.ai_resolved)
        transferred_count = sum(1 for s in sessions if s.transferred_to_human)

        # 节省的人力成本（AI 解决 = 不需要人工）
        human_cost_saved = ai_resolved_count * (self.human_cost / 60) * self.human_handle_min

        # AI 自身成本
        ai_cost = sum(s.llm_cost for s in sessions)
        # 知识库摊销
        kb_amortized = self.kb_monthly_cost / 30  # 按天摊销
        ai_total_cost = ai_cost + kb_amortized

        # 净节省
        net_saved = human_cost_saved - ai_total_cost

        # ROI
        roi = (net_saved / ai_total_cost * 100) if ai_total_cost > 0 else 0.0

        # 单次成本对比
        cost_per_ai_case = ai_total_cost / n
        cost_per_human_case = (self.human_cost / 60) * self.human_handle_min
        cost_reduction_pct = (
            (cost_per_human_case - cost_per_ai_case) / cost_per_human_case * 100
        ) if cost_per_human_case > 0 else 0.0

        return {
            "ai_resolved_count": ai_resolved_count,
            "transferred_count": transferred_count,
            "human_cost_saved_yuan": round(human_cost_saved, 2),
            "ai_total_cost_yuan": round(ai_total_cost, 2),
            "net_saved_yuan": round(net_saved, 2),
            "ROI_pct": round(roi, 2),
            "cost_per_ai_case": round(cost_per_ai_case, 4),
            "cost_per_human_case": round(cost_per_human_case, 4),
            "cost_reduction_pct": round(cost_reduction_pct, 2),
        }

    def _session_cost(self, session: BusinessSession) -> float:
        """单次会话成本"""
        llm = session.llm_cost
        human_assist = (self.human_cost / 60) * session.human_assist_minutes
        return llm + human_assist


# ============================================================
# Badcase 周会分析器
# ============================================================

class BadcaseAnalyzer:
    """
    Badcase 周会分析器
    - 每周抽 30 条 badcase（10 转人工 + 10 差评 + 10 假解决）
    - 分类：评分偏差 / 知识错误 / 建议不匹配 / 用户投诉
    - 定级：P0 (24h) / P1 (3d) / P2 (1w)
    """

    P0_CRITICAL = ["合规风险", "金钱损失", "严重投诉", "多人反馈同一问题"]
    P1_MAJOR = ["单向不匹配", "单条差评", "中等幻觉"]
    P2_MINOR = ["边界 case", "小偏差", "用户主观差异"]

    @staticmethod
    def classify_badcase(badcase: Dict) -> Tuple[str, str, int]:
        """
        对 badcase 分类 + 定级
        Returns: (category, level, fix_hours)
        """
        # 检测合规类
        if "compliance" in badcase.get("flags", []):
            return "合规风险", "P0", 24
        # 金钱损失
        if badcase.get("money_impact", 0) > 0:
            return "金钱损失", "P0", 24
        # 多人反馈
        if badcase.get("repeat_count", 0) >= 3:
            return "高频错误", "P0", 24
        # 单向不匹配
        if "intent_mismatch" in badcase.get("flags", []):
            return "建议不匹配", "P1", 72
        # 知识错误
        if "knowledge_error" in badcase.get("flags", []):
            return "知识错误", "P1", 72
        # 默认
        return "边界 case", "P2", 168

    @staticmethod
    def weekly_report(badcases: List[Dict]) -> Dict:
        """生成周报摘要"""
        if not badcases:
            return {"total": 0}

        by_category = defaultdict(int)
        by_level = defaultdict(int)
        p0_issues = []

        for bc in badcases:
            category, level, fix_hours = BadcaseAnalyzer.classify_badcase(bc)
            by_category[category] += 1
            by_level[level] += 1
            if level == "P0":
                p0_issues.append({
                    "session_id": bc.get("session_id"),
                    "category": category,
                    "user_question": bc.get("question", "")[:100],
                    "ai_answer": bc.get("answer", "")[:100],
                    "fix_within_hours": fix_hours,
                })

        return {
            "total": len(badcases),
            "by_category": dict(by_category),
            "by_level": dict(by_level),
            "p0_critical_issues": p0_issues,
            "action_items": [
                f"修复 {len(p0_issues)} 个 P0 关键问题（24 小时内）",
                f"覆盖 {by_category.get('知识错误', 0)} 个知识库条目",
                f"优化 {by_category.get('建议不匹配', 0)} 个意图规则",
            ],
        }


# ============================================================
# CLI 入口
# ============================================================

def main():
    print("=" * 70)
    print("业务指标体系 — 对齐客服中心业界四象限")
    print("=" * 70)
    print()
    print("【7 大业务指标】")
    print()
    for cat in MetricCategory:
        print(f"  [{cat.value.upper()}]")
    print()
    print("【分层评估 — L1/L2/L3】")
    for tier, intents in TIER_MAPPING.items():
        print(f"  {tier.value}: {len(intents)} 种意图")
        for intent in intents:
            print(f"    - {intent}")
    print()
    print("【四象限联动诊断】")
    print("  A: 响应快 + 转人工高 = 回复快但没用")
    print("  B: FCR 高 + CSAT 低   = 机械解决但态度差")
    print("  C: 转人工低 + CSAT 低 = AI 在硬撑（危险）")
    print("  D: 响应慢 + FCR 高   = 慢但靠谱")
    print()
    print("=" * 70)
    print()
    print("使用示例：")
    print("  from src.eval.business_metrics import BusinessMetricsCalculator, BusinessSession")
    print("  calc = BusinessMetricsCalculator()")
    print("  report = calc.compute_kpis(sessions, period='2026-05')")
    print("  print(report.to_dict())")


if __name__ == "__main__":
    main()
