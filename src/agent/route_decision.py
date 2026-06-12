"""
v3.4.0-b 5 路径路由决策器
==========================

业界对齐: 招行小招 / 微众银行 / 蚂蚁客服 都在 2025-2026 转向 5 路径路由
- 路径 1: L0_HUMAN       红线/紧急 -> 100% 转人工
- 路径 2: BIZ_DB_API     业务查询 -> 调业务数据库 (Text2SQL / API)
- 路径 3: AGENT_TOOL     工具意图 -> 调 Agent (v3.4.0 暂不做, v3.5.0 计划)
- 路径 4: RAG_KB         信息咨询 -> RAG 检索
- 路径 5: CASCADE_TPL    业务办理 -> Cascade 模板

设计:
1. 5 路径优先级固定 (L0 > BIZ_DB > AGENT > RAG > CASCADE)
2. 每条 query 只能走 1 条路径
3. 路径可观测 (返回 path + reason + decision_id)
4. 0 依赖 (纯 dict + str 决策)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# 路径常量
PATH_L0_HUMAN = "L0_HUMAN"           # 红线/紧急
PATH_BIZ_DB = "BIZ_DB_API"           # 业务数据库
PATH_AGENT = "AGENT_TOOL"            # 工具调用 (暂不做)
PATH_RAG = "RAG_KB"                  # 知识库检索
PATH_CASCADE = "CASCADE_TEMPLATE"    # Cascade 模板

# 优先级数字 (越小越优先)
PATH_PRIORITY = {
    PATH_L0_HUMAN: 1,
    PATH_BIZ_DB: 2,
    PATH_AGENT: 3,
    PATH_RAG: 4,
    PATH_CASCADE: 5,
}

# Agent 暂不做的意图前缀 (产品决策: 不确定能交付的能力不要承诺)
AGENT_DEFERRED_INTENT_PREFIXES = (
    "biz_card_activate",  # 卡片激活 (跳转 App)
    "biz_card_loss",      # 挂失 (跳转 95555)
    "biz_card_reissue",   # 补卡 (跳转网点)
    "biz_pwd_reset",      # 密码重置 (跳转 App)
    "biz_pay_repay",      # 主动还款 (跳转 App)
    "biz_pay_autopay",    # 自动还款设置 (跳转 App)
    "biz_installment",    # 分期 (跳转 App)
)

# 业务数据库意图 (调 mock DB)
BIZ_DB_INTENT_KEYWORDS = (
    "账单", "还款日", "最低还款", "积分", "余额", "明细", "流水", "转账记录",
    "贷款进度", "申请进度", "信用卡申请", "卡片邮寄", "对账单", "物流", "快递", "邮寄",
)

# 工具意图 (跳转到 App, v3.4.0 替代方案)
TOOL_INTENT_KEYWORDS = (
    "激活", "挂失", "补卡", "改地址", "改密码", "重置密码",
    "还款", "自动还款", "分期", "调额", "注销",
)


@dataclass
class RouteDecision:
    """路由决策结果"""
    path: str  # 5 路径之一
    reason: str
    priority: int
    intent: str
    l0_triggered: bool = False
    target_resource: Optional[str] = None  # 具体走的资源 (e.g. "biz_db.bill")
    fallback: Optional[str] = None  # 兜底路径


class RouteDecisionMaker:
    """5 路径路由决策器"""

    def __init__(self, intent_recognizer=None, l0_checker=None, biz_db=None):
        """
        Args:
            intent_recognizer: 意图识别器 (可选, 用于调意图)
            l0_checker: L0 红线检查器 (可选, 复用 v3.3.7 banking_l0_dict)
            biz_db: 业务数据库 mock (可选, 复用 v3.4.0-b BizDBMock)
        """
        self.intent_recognizer = intent_recognizer
        self.l0_checker = l0_checker
        self.biz_db = biz_db

    def decide(
        self,
        user_input: str,
        intent: str = "",
        intent_conf: float = 1.0,
        l0_triggered: bool = False,
    ) -> RouteDecision:
        """
        决策 query 走哪条路径
        """
        # 路径 1: L0 红线 -> 100% 转人工
        # (含两种: 显式 l0_triggered=True, 或 cons_urg_human 类紧急转人工意图)
        is_urg_human = (
            intent.startswith("cons_urg_human")
            or "转人工" in user_input
            or "人工服务" in user_input
        )
        if l0_triggered or is_urg_human:
            return RouteDecision(
                path=PATH_L0_HUMAN,
                reason=f"{'L0 红线触发' if l0_triggered else '紧急转人工意图'}, 100% 转人工 (input: {user_input[:30]})",
                priority=PATH_PRIORITY[PATH_L0_HUMAN],
                intent=intent,
                l0_triggered=True,
                target_resource="human_agent",
            )

        # 路径 2: 业务数据库 (账单/明细/物流 类)
        biz_match = self._match_biz_db(user_input, intent)
        if biz_match:
            return RouteDecision(
                path=PATH_BIZ_DB,
                reason=f"业务数据库查询: {biz_match}",
                priority=PATH_PRIORITY[PATH_BIZ_DB],
                intent=intent,
                target_resource=f"biz_db.{biz_match}",
                fallback=PATH_CASCADE,  # 兜底走模板
            )

        # 路径 3: 工具意图 -> Agent (v3.4.0 暂不做, 给跳转接口)
        tool_match = self._match_agent(user_input, intent)
        if tool_match:
            return RouteDecision(
                path=PATH_AGENT,
                reason=f"工具意图: {tool_match} (v3.4.0 暂不调 Agent, 给跳转接口)",
                priority=PATH_PRIORITY[PATH_AGENT],
                intent=intent,
                target_resource=f"agent.{tool_match}",
                fallback=PATH_CASCADE,  # 兜底走模板 (含跳转链接)
            )

        # 路径 4: 业务办理 -> Cascade 模板
        if intent.startswith("biz_") or intent.startswith("sys_"):
            return RouteDecision(
                path=PATH_CASCADE,
                reason=f"业务办理意图 ({intent}), 走 Cascade 模板 (L1 模板 / L2 RAG / L3 LLM)",
                priority=PATH_PRIORITY[PATH_CASCADE],
                intent=intent,
            )

        # 路径 5: 信息咨询/营销 -> RAG 检索
        if intent.startswith("info_") or intent.startswith("sales_") or intent.startswith("cons_"):
            return RouteDecision(
                path=PATH_RAG,
                reason=f"信息咨询意图 ({intent}), 走 RAG 知识库检索",
                priority=PATH_PRIORITY[PATH_RAG],
                intent=intent,
            )

        # 兜底: 全部 LLM
        return RouteDecision(
            path=PATH_CASCADE,
            reason=f"未识别意图 ({intent}), 兜底走 L3 LLM",
            priority=99,
            intent=intent,
            fallback=PATH_CASCADE,
        )

    def _match_biz_db(self, user_input: str, intent: str) -> Optional[str]:
        """匹配业务数据库的具体资源"""
        u = user_input.lower()
        for kw in BIZ_DB_INTENT_KEYWORDS:
            if kw in user_input:
                if "账单" in user_input and ("多少" in user_input or "还" in user_input or "金额" in user_input):
                    return "bill"
                if "物流" in user_input or "邮寄" in user_input or "快递" in user_input:
                    return "logistics"
                if "明细" in user_input or "流水" in user_input:
                    return "transaction"
                if "余额" in user_input:
                    return "balance"
                if "积分" in user_input:
                    return "points"
                if "进度" in user_input:
                    return "progress"
        return None

    def _match_agent(self, user_input: str, intent: str) -> Optional[str]:
        """匹配工具意图"""
        # 优先看 intent 前缀
        for prefix in AGENT_DEFERRED_INTENT_PREFIXES:
            if intent.startswith(prefix):
                return prefix.replace("biz_", "").replace("_", "")
        # 兜底看关键词
        for kw in TOOL_INTENT_KEYWORDS:
            if kw in user_input:
                return kw
        return None


# ============================================================
# 工厂 + 决策日志
# ============================================================
_decision_log: List[RouteDecision] = []


def get_decision_maker(intent_recognizer=None, l0_checker=None, biz_db=None) -> RouteDecisionMaker:
    """获取路由决策器"""
    return RouteDecisionMaker(intent_recognizer, l0_checker, biz_db)


def log_decision(decision: RouteDecision):
    """记录决策日志 (可观测性)"""
    _decision_log.append(decision)


def get_decision_log() -> List[RouteDecision]:
    """获取决策日志"""
    return _decision_log.copy()


def get_path_distribution() -> Dict[str, int]:
    """路径分布统计 (给 Badcase 分析用)"""
    dist: Dict[str, int] = {}
    for d in _decision_log:
        dist[d.path] = dist.get(d.path, 0) + 1
    return dist
