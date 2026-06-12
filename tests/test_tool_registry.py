"""
测试 13: v3.5.0 Mock 工具调用 (read-only 查询工具)
==================================================
覆盖:
- 5 个查询工具 (账单/积分/额度/理财/物流)
- 工具注册表
- 审计日志
- 工具意图映射
"""
import pytest

from src.agent.tool_registry import (
    ToolRegistry,
    ToolResult,
    BaseTool,
    QueryBillTool,
    QueryPointsTool,
    QueryLimitTool,
    QueryWealthTool,
    QueryLogisticsTool,
    INTENT_TO_TOOL,
    get_tool_registry,
)


class TestQueryTools:
    """5 个查询工具测试"""

    def test_query_bill(self):
        """查询账单"""
        tool = QueryBillTool()
        r = tool.run(customer_id="C001")
        assert r.success is True
        assert r.data["amount"] == 12345.67
        assert r.tool_name == "query_bill"
        assert r.elapsed_ms >= 0

    def test_query_bill_no_customer(self):
        """无客户 ID"""
        tool = QueryBillTool()
        r = tool.run(customer_id="")
        assert r.success is False
        assert "missing customer_id" in r.error

    def test_query_bill_not_found(self):
        """客户不存在"""
        tool = QueryBillTool()
        r = tool.run(customer_id="C999")
        assert r.success is False
        assert "账单不存在" in r.error

    def test_query_points(self):
        """查询积分"""
        tool = QueryPointsTool()
        r = tool.run(customer_id="C001")
        assert r.success is True
        assert r.data["points"] > 0
        assert r.data["unit"] == "积分"

    def test_query_limit(self):
        """查询额度"""
        tool = QueryLimitTool()
        r = tool.run(customer_id="C001")
        assert r.success is True
        assert r.data["total"] == 50000
        assert r.data["available"] == 37654.33

    def test_query_wealth_all(self):
        """查询所有理财"""
        tool = QueryWealthTool()
        r = tool.run()
        assert r.success is True
        assert len(r.data) >= 1

    def test_query_wealth_by_risk(self):
        """按风险等级查"""
        tool = QueryWealthTool()
        r = tool.run(risk_level="R1")
        assert r.success is True
        for w in r.data:
            assert "R1" in w.get("risk_level", "")

    def test_query_logistics(self):
        """查询物流"""
        tool = QueryLogisticsTool()
        r = tool.run(customer_id="C001")
        assert r.success is True
        assert r.data["carrier"] == "顺丰"

    def test_query_logistics_not_found(self):
        """物流不存在"""
        tool = QueryLogisticsTool()
        r = tool.run(customer_id="C999")
        assert r.success is False


class TestToolRegistry:
    """工具注册表测试"""

    @pytest.fixture
    def reg(self):
        return get_tool_registry()

    def test_list_tools(self, reg):
        """列出工具"""
        tools = reg.list_tools()
        names = [t["name"] for t in tools]
        assert "query_bill" in names
        assert "query_points" in names
        assert "query_limit" in names
        assert "query_wealth" in names
        assert "query_logistics" in names
        assert len(tools) == 5

    def test_get_tool(self, reg):
        """获取工具"""
        tool = reg.get("query_bill")
        assert tool is not None
        assert tool.name == "query_bill"

    def test_call_tool(self, reg):
        """调用工具"""
        r = reg.call("query_bill", customer_id="C001")
        assert r.success is True
        assert r.data["amount"] == 12345.67

    def test_call_unknown_tool(self, reg):
        """调用未知工具"""
        r = reg.call("nonexistent_tool")
        assert r.success is False
        assert "not found" in r.error

    def test_audit_log(self, reg):
        """审计日志"""
        reg.call("query_bill", customer_id="C001")
        reg.call("query_points", customer_id="C001")
        log = reg.get_audit_log()
        assert len(log) >= 2
        for entry in log:
            assert "tool" in entry
            assert "ts" in entry
            assert "success" in entry

    def test_register_custom_tool(self, reg):
        """注册自定义工具"""
        class MyTool(BaseTool):
            name = "my_tool"
            description = "my custom tool"
            def run(self, **kwargs):
                return ToolResult(success=True, data="ok", tool_name=self.name)
        reg.register(MyTool())
        r = reg.call("my_tool")
        assert r.success is True
        assert r.data == "ok"


class TestIntentToToolMapping:
    """意图 -> 工具映射测试"""

    def test_bill_intent_maps_to_query_bill(self):
        """账单意图 -> query_bill"""
        assert INTENT_TO_TOOL["info_bill_amount"] == "query_bill"

    def test_points_intent_maps_to_query_points(self):
        """积分意图 -> query_points"""
        assert INTENT_TO_TOOL["info_bill_point"] == "query_points"

    def test_wealth_intent_maps_to_query_wealth(self):
        """理财意图 -> query_wealth"""
        assert INTENT_TO_TOOL["sales_wealth_prod"] == "query_wealth"
