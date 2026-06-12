"""
v3.5.0 Mock 工具调用 (read-only 查询工具)
===========================================

业界对齐: 招行小招 / 蚂蚁 / 微众 2025-2026 都在用 LangChain / LlamaIndex Tool
v3.5.0 范围 (产品决策):
- 只做 read-only 查询工具 (不改写)
- 真实改写 (激活/挂失/还款) 仍走 v3.4.0 跳转接口
- Tool 接口对齐 LangChain (Tool(name, description, func))

设计:
- 5 个查询工具: 查账单/查积分/查额度/查理财/查物流
- 客户身份校验 (CID + 4 要素 mock)
- 调用审计日志 (满足银保监要求)
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

try:
    from src.rag.knowledge_base_v2 import get_biz_db
except ImportError:
    get_biz_db = None


# ============================================================
# 工具调用结果
# ============================================================
@dataclass
class ToolResult:
    """工具调用结果"""
    success: bool
    data: Any
    error: Optional[str] = None
    tool_name: str = ""
    elapsed_ms: float = 0.0
    audit_log: Dict[str, Any] = field(default_factory=dict)


# ============================================================
# 工具基类
# ============================================================
class BaseTool:
    """工具基类 (LangChain Tool 接口对齐)"""

    name: str = ""
    description: str = ""
    requires_auth: bool = True

    def run(self, **kwargs) -> ToolResult:
        raise NotImplementedError

    def audit(self, kwargs: Dict, result: ToolResult) -> Dict:
        """审计日志 (满足银保监要求)"""
        return {
            "tool": self.name,
            "ts": time.time(),
            "input": {k: v for k, v in kwargs.items() if k != "auth_token"},
            "success": result.success,
            "elapsed_ms": result.elapsed_ms,
        }


# ============================================================
# 5 个查询工具
# ============================================================
class QueryBillTool(BaseTool):
    """查询信用卡账单"""
    name = "query_bill"
    description = "查询客户的信用卡账单金额、还款日、状态"

    def run(self, customer_id: str = "", **kwargs) -> ToolResult:
        t0 = time.time()
        if not customer_id:
            return ToolResult(success=False, data=None, error="missing customer_id", tool_name=self.name)
        if get_biz_db is None:
            return ToolResult(success=False, data=None, error="biz_db unavailable", tool_name=self.name)
        db = get_biz_db()
        bill = db.query_bill_amount(customer_id)
        elapsed = (time.time() - t0) * 1000
        if bill is None:
            r = ToolResult(success=False, data=None, error="账单不存在", tool_name=self.name, elapsed_ms=elapsed)
        else:
            r = ToolResult(success=True, data=bill, tool_name=self.name, elapsed_ms=elapsed)
        r.audit_log = self.audit({"customer_id": customer_id}, r)
        return r


class QueryPointsTool(BaseTool):
    """查询信用卡积分"""
    name = "query_points"
    description = "查询客户的信用卡积分余额"

    def run(self, customer_id: str = "", **kwargs) -> ToolResult:
        t0 = time.time()
        if not customer_id:
            return ToolResult(success=False, data=None, error="missing customer_id", tool_name=self.name)
        # mock: 积分 = 客户ID 末位 × 1000
        try:
            points = int(customer_id[-1]) * 1000 + 500
        except Exception:
            points = 0
        elapsed = (time.time() - t0) * 1000
        r = ToolResult(
            success=True,
            data={"customer_id": customer_id, "points": points, "unit": "积分"},
            tool_name=self.name,
            elapsed_ms=elapsed,
        )
        r.audit_log = self.audit({"customer_id": customer_id}, r)
        return r


class QueryLimitTool(BaseTool):
    """查询信用卡可用额度"""
    name = "query_limit"
    description = "查询客户的信用卡可用额度"

    def run(self, customer_id: str = "", **kwargs) -> ToolResult:
        t0 = time.time()
        if not customer_id:
            return ToolResult(success=False, data=None, error="missing customer_id", tool_name=self.name)
        # mock: 额度根据客户ID
        mock_limits = {
            "C001": {"total": 50000, "available": 37654.33},
            "C002": {"total": 30000, "available": 21111.12},
            "C003": {"total": 80000, "available": 79499.50},
        }
        data = mock_limits.get(customer_id, {"total": 10000, "available": 10000})
        elapsed = (time.time() - t0) * 1000
        r = ToolResult(
            success=True,
            data={**data, "customer_id": customer_id, "currency": "CNY"},
            tool_name=self.name,
            elapsed_ms=elapsed,
        )
        r.audit_log = self.audit({"customer_id": customer_id}, r)
        return r


class QueryWealthTool(BaseTool):
    """查询理财产品"""
    name = "query_wealth"
    description = "查询可购买的理财产品列表"

    def run(self, risk_level: str = "", **kwargs) -> ToolResult:
        t0 = time.time()
        if get_biz_db is None:
            return ToolResult(success=False, data=None, error="biz_db unavailable", tool_name=self.name)
        db = get_biz_db()
        wealths = db.query_wealth_products()
        if risk_level:
            wealths = [w for w in wealths if risk_level in w.get("risk_level", "")]
        elapsed = (time.time() - t0) * 1000
        r = ToolResult(success=True, data=wealths, tool_name=self.name, elapsed_ms=elapsed)
        r.audit_log = self.audit({"risk_level": risk_level}, r)
        return r


class QueryLogisticsTool(BaseTool):
    """查询卡片/对账单物流"""
    name = "query_logistics"
    description = "查询客户的卡片邮寄或对账单邮寄物流信息"

    def run(self, customer_id: str = "", **kwargs) -> ToolResult:
        t0 = time.time()
        if not customer_id:
            return ToolResult(success=False, data=None, error="missing customer_id", tool_name=self.name)
        if get_biz_db is None:
            return ToolResult(success=False, data=None, error="biz_db unavailable", tool_name=self.name)
        db = get_biz_db()
        log = db.query_logistics(customer_id)
        elapsed = (time.time() - t0) * 1000
        if log is None:
            r = ToolResult(success=False, data=None, error="物流不存在", tool_name=self.name, elapsed_ms=elapsed)
        else:
            r = ToolResult(success=True, data=log, tool_name=self.name, elapsed_ms=elapsed)
        r.audit_log = self.audit({"customer_id": customer_id}, r)
        return r


# ============================================================
# 工具注册表 (类似 LangChain Tool registry)
# ============================================================
class ToolRegistry:
    """工具注册表"""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        # 注册 5 个查询工具
        self.register(QueryBillTool())
        self.register(QueryPointsTool())
        self.register(QueryLimitTool())
        self.register(QueryWealthTool())
        self.register(QueryLogisticsTool())
        self._audit_log: List[Dict] = []

    def register(self, tool: BaseTool):
        """注册工具"""
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[BaseTool]:
        """获取工具"""
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, str]]:
        """列出所有工具"""
        return [{"name": t.name, "description": t.description} for t in self._tools.values()]

    def call(self, name: str, **kwargs) -> ToolResult:
        """调用工具"""
        tool = self.get(name)
        if tool is None:
            return ToolResult(success=False, data=None, error=f"tool '{name}' not found")
        result = tool.run(**kwargs)
        if result.audit_log:
            self._audit_log.append(result.audit_log)
        return result

    def get_audit_log(self) -> List[Dict]:
        """获取审计日志 (银保监要求)"""
        return self._audit_log.copy()


# ============================================================
# 工具意图 -> Tool 映射 (路由用)
# ============================================================
INTENT_TO_TOOL = {
    "info_bill_amount": "query_bill",
    "info_bill_point": "query_points",
    "info_bill_min": "query_bill",
    "info_acc_balance": "query_limit",  # 余额 = 额度 - 已用
    "info_logistics": "query_logistics",
    "info_prog_application": "query_logistics",  # 申请进度可能查物流
    "sales_wealth_prod": "query_wealth",
    "cons_wealth_recommend": "query_wealth",
}


# ============================================================
# 工厂
# ============================================================
def get_tool_registry() -> ToolRegistry:
    """获取工具注册表"""
    return ToolRegistry()
