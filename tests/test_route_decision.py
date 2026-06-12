"""
测试 8: v3.4.0-b 5 路径路由决策器
==================================
覆盖:
- 5 路径优先级
- L0 红线 -> L0_HUMAN
- 业务查询 -> BIZ_DB_API
- 工具意图 -> AGENT_TOOL
- 信息咨询 -> RAG_KB
- 业务办理 -> CASCADE_TEMPLATE
- 转人工
- 决策日志
"""
import pytest

from src.agent.route_decision import (
    RouteDecisionMaker,
    RouteDecision,
    PATH_L0_HUMAN, PATH_BIZ_DB, PATH_AGENT, PATH_RAG, PATH_CASCADE,
    PATH_PRIORITY,
    BIZ_DB_INTENT_KEYWORDS,
    TOOL_INTENT_KEYWORDS,
    get_decision_maker,
    log_decision,
    get_decision_log,
    get_path_distribution,
)


class TestRouteDecisionPaths:
    """5 路径路由决策测试"""

    @pytest.fixture
    def dm(self):
        return get_decision_maker()

    def test_l0_triggered_routes_to_human(self, dm):
        """L0 红线触发 -> L0_HUMAN"""
        d = dm.decide("我被骗了 10000", "sec_fraud_report", 0.95, l0_triggered=True)
        assert d.path == PATH_L0_HUMAN
        assert d.priority == PATH_PRIORITY[PATH_L0_HUMAN]
        assert d.l0_triggered is True

    def test_urg_human_intent_routes_to_human(self, dm):
        """cons_urg_human 意图 -> L0_HUMAN (自动识别)"""
        d = dm.decide("转人工", "cons_urg_human", 0.95)
        assert d.path == PATH_L0_HUMAN

    def test_human_transfer_keyword_routes_to_human(self, dm):
        """"转人工" 关键词 -> L0_HUMAN"""
        d = dm.decide("我要转人工", "info_acc_balance", 0.9)
        assert d.path == PATH_L0_HUMAN

    def test_bill_query_routes_to_biz_db(self, dm):
        """账单查询 -> BIZ_DB"""
        d = dm.decide("我的信用卡账单多少", "info_bill_amount", 0.9)
        assert d.path == PATH_BIZ_DB
        assert "bill" in d.target_resource

    def test_balance_query_routes_to_biz_db(self, dm):
        """余额查询 -> BIZ_DB"""
        d = dm.decide("我账户余额多少", "info_acc_balance", 0.9)
        assert d.path == PATH_BIZ_DB

    def test_logistics_query_routes_to_biz_db(self, dm):
        """物流查询 -> BIZ_DB"""
        d = dm.decide("我的快递到哪了", "info_logistics", 0.85)
        assert d.path == PATH_BIZ_DB
        assert "logistics" in d.target_resource

    def test_card_activate_intent_routes_to_agent(self, dm):
        """卡片激活工具意图 -> AGENT_TOOL (v3.4.0 暂不做)"""
        d = dm.decide("怎么激活信用卡", "biz_card_activate", 0.85)
        assert d.path == PATH_AGENT
        assert "v3.4.0 暂不调 Agent" in d.reason

    def test_password_reset_intent_routes_to_agent(self, dm):
        """密码重置工具意图 -> AGENT_TOOL"""
        d = dm.decide("密码忘了怎么重置", "biz_pwd_reset", 0.85)
        assert d.path == PATH_AGENT

    def test_sales_intent_routes_to_rag(self, dm):
        """销售/产品类 -> RAG_KB"""
        d = dm.decide("办什么信用卡好", "sales_credit_prod", 0.85)
        assert d.path == PATH_RAG

    def test_info_intent_routes_to_rag(self, dm):
        """信息咨询类 -> RAG_KB"""
        d = dm.decide("理财有什么推荐", "sales_wealth_prod", 0.88)
        assert d.path == PATH_RAG

    def test_biz_intent_routes_to_cascade(self, dm):
        """业务办理类 -> CASCADE"""
        d = dm.decide("你好", "sys_greeting", 0.99)
        assert d.path == PATH_CASCADE

    def test_unknown_intent_falls_back_to_cascade(self, dm):
        """未知意图兜底 -> CASCADE"""
        d = dm.decide("asdfgh", "unknown_xyz", 0.3)
        assert d.path == PATH_CASCADE
        assert d.priority == 99

    def test_priority_order(self):
        """路径优先级固定 (L0 > BIZ_DB > AGENT > RAG > CASCADE)"""
        assert PATH_PRIORITY[PATH_L0_HUMAN] < PATH_PRIORITY[PATH_BIZ_DB]
        assert PATH_PRIORITY[PATH_BIZ_DB] < PATH_PRIORITY[PATH_AGENT]
        assert PATH_PRIORITY[PATH_AGENT] < PATH_PRIORITY[PATH_RAG]
        assert PATH_PRIORITY[PATH_RAG] < PATH_PRIORITY[PATH_CASCADE]


class TestRouteDecisionStructure:
    """RouteDecision 数据类测试"""

    def test_to_dict_fields(self):
        """to_dict 字段完整"""
        d = RouteDecision(
            path=PATH_BIZ_DB,
            reason="业务查询",
            priority=2,
            intent="info_bill",
        )
        d_dict = d.to_dict() if hasattr(d, "to_dict") else d.__dict__
        for k in ["path", "reason", "priority", "intent"]:
            assert k in d_dict


class TestDecisionLog:
    """决策日志测试"""

    def test_log_and_get(self):
        """记录 + 获取"""
        before = len(get_decision_log())
        d = RouteDecision(
            path=PATH_RAG, reason="test", priority=4, intent="info_test"
        )
        log_decision(d)
        after = len(get_decision_log())
        assert after == before + 1

    def test_path_distribution(self):
        """路径分布统计"""
        # 清空
        log_decision.__globals__["_decision_log"].clear()
        # 加 5 条 (3 RAG + 2 BIZ_DB)
        for i in range(3):
            log_decision(RouteDecision(path=PATH_RAG, reason="r", priority=4, intent=f"i{i}"))
        for i in range(2):
            log_decision(RouteDecision(path=PATH_BIZ_DB, reason="b", priority=2, intent=f"i{i}"))
        dist = get_path_distribution()
        assert dist.get(PATH_RAG, 0) == 3
        assert dist.get(PATH_BIZ_DB, 0) == 2
        # 清空
        log_decision.__globals__["_decision_log"].clear()


class TestKeywordSets:
    """关键词集测试"""

    def test_biz_db_keywords_contains_common(self):
        """业务数据库关键词含常见查询词"""
        for kw in ["账单", "余额", "明细", "物流", "快递"]:
            assert kw in BIZ_DB_INTENT_KEYWORDS

    def test_tool_keywords_contains_common(self):
        """工具意图关键词含常见操作"""
        for kw in ["激活", "挂失", "补卡", "还款"]:
            assert kw in TOOL_INTENT_KEYWORDS
