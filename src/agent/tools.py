"""
模拟银行业务工具
实际不连接真实系统，仅用于演示
"""
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import random


@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    data: Any
    message: str
    tool_name: str


class BankingTools:
    """
    模拟银行业务工具
    """

    @staticmethod
    def check_balance(account_id: str) -> ToolResult:
        """查询账户余额（模拟）"""
        # 模拟余额数据
        balance = round(random.uniform(1000, 100000), 2)
        return ToolResult(
            success=True,
            data={"account_id": account_id, "balance": balance, "currency": "CNY"},
            message=f"账户 {account_id} 余额为 {balance} 元",
            tool_name="check_balance"
        )

    @staticmethod
    def query_bill(card_id: str, month: str = None) -> ToolResult:
        """查询信用卡账单（模拟）"""
        if month is None:
            from datetime import datetime
            month = datetime.now().strftime("%Y-%m")

        # 模拟账单数据
        bill_amount = round(random.uniform(500, 50000), 2)
        min_payment = round(bill_amount * 0.1, 2)
        due_date = datetime.now() + timedelta(days=15)

        return ToolResult(
            success=True,
            data={
                "card_id": card_id,
                "billing_date": f"{month}-01",
                "total_amount": bill_amount,
                "min_payment": min_payment,
                "due_date": due_date.strftime("%Y-%m-%d"),
                "points": random.randint(0, 10000)
            },
            message=f"您{month}月的账单金额为 {bill_amount} 元，最低还款 {min_payment} 元，到期日 {due_date.strftime('%Y-%m-%d')}",
            tool_name="query_bill"
        )

    @staticmethod
    def search_branch(city: str = None, district: str = None) -> ToolResult:
        """查询银行网点（模拟）"""
        # 模拟网点数据
        branches = [
            {"name": "招商银行佛山分行", "address": "佛山市禅城区祖庙路1号", "phone": "0757-82345678", "hours": "9:00-17:00"},
            {"name": "招商银行禅城支行", "address": "佛山市禅城区季华五路28号", "phone": "0757-82345679", "hours": "9:00-17:00"},
            {"name": "招商银行南海支行", "address": "佛山市南海区桂城街道南海大道18号", "phone": "0757-86234567", "hours": "9:00-17:00"},
        ]

        if city:
            branches = [b for b in branches if city in b["name"] or city in b["address"]]

        return ToolResult(
            success=True,
            data=branches,
            message=f"找到 {len(branches)} 个网点",
            tool_name="search_branch"
        )

    @staticmethod
    def get_product_info(product_type: str = "all") -> ToolResult:
        """查询产品信息（模拟）"""
        products = {
            "理财": [
                {"name": "增利系列", "risk": "中低", "min_amount": "10000", "period": "3-12个月", "expected_return": "3.5%-4.5%"},
                {"name": "稳稳盈", "risk": "低", "min_amount": "5000", "period": "6个月", "expected_return": "3.2%-3.8%"},
            ],
            "存款": [
                {"name": "大额存单", "risk": "无", "min_amount": "200000", "period": "1-3年", "expected_return": "2.1%-2.9%"},
                {"name": "定期存款", "risk": "无", "min_amount": "50", "period": "3个月-5年", "expected_return": "1.5%-2.75%"},
            ],
            "贷款": [
                {"name": "信用贷款", "risk": "-", "min_amount": "10000", "period": "最长5年", "max_amount": "500000"},
                {"name": "房贷", "risk": "-", "min_amount": "100000", "period": "最长30年", "max_amount": "无上限"},
            ]
        }

        if product_type == "all":
            return ToolResult(
                success=True,
                data=products,
                message="我行主要产品包括理财、存款、贷款三大类",
                tool_name="get_product_info"
            )
        else:
            return ToolResult(
                success=True,
                data=products.get(product_type, []),
                message=f"{product_type}类产品信息",
                tool_name="get_product_info"
            )

    @staticmethod
    def card_loss_report(card_id: str) -> ToolResult:
        """信用卡挂失（模拟）"""
        return ToolResult(
            success=True,
            data={"card_id": card_id, "report_time": datetime.now().isoformat(), "status": "挂失成功"},
            message=f"您的信用卡 {card_id} 已成功挂失，新卡将在3-5个工作日内寄出",
            tool_name="card_loss_report"
        )

    @staticmethod
    def transfer_guide(amount: float = None, target_bank: str = None) -> ToolResult:
        """转账指引（模拟）"""
        guide = """
转账操作步骤：
1. 打开招商银行手机APP
2. 点击首页"转账"
3. 选择"转账到银行卡"
4. 输入收款人信息：
   - 收款人姓名
   - 收款卡号
   - 开户银行
5. 输入转账金额
6. 选择转账方式（实时/普通）
7. 确认信息并输入密码完成转账

注意事项：
- 转账限额：单笔最高50万，日累计最高100万
- 跨行转账可能收取手续费，标准请查看APP内"转账手续费"
- 请核实收款人信息，转账后无法撤销
"""

        return ToolResult(
            success=True,
            data={"guide": guide, "transfer_amount": amount, "target_bank": target_bank},
            message=guide.strip(),
            tool_name="transfer_guide"
        )

    @staticmethod
    def schedule_human_service(session_id: str, reason: str = None) -> ToolResult:
        """预约人工服务（模拟）"""
        return ToolResult(
            success=True,
            data={"session_id": session_id, "wait_time": "预计等待5-10分钟", "queue_number": random.randint(1, 99)},
            message="已为您预约人工服务，当前预计等待5-10分钟，请稍候",
            tool_name="schedule_human_service"
        )


# 工具注册表
BANKING_TOOLS = {
    "check_balance": BankingTools.check_balance,
    "query_bill": BankingTools.query_bill,
    "search_branch": BankingTools.search_branch,
    "get_product_info": BankingTools.get_product_info,
    "card_loss_report": BankingTools.card_loss_report,
    "transfer_guide": BankingTools.transfer_guide,
    "schedule_human_service": BankingTools.schedule_human_service,
}


def execute_tool(tool_name: str, **kwargs) -> ToolResult:
    """执行工具"""
    if tool_name not in BANKING_TOOLS:
        return ToolResult(
            success=False,
            data=None,
            message=f"未知工具: {tool_name}",
            tool_name=tool_name
        )

    try:
        return BANKING_TOOLS[tool_name](**kwargs)
    except Exception as e:
        return ToolResult(
            success=False,
            data=None,
            message=f"工具执行错误: {str(e)}",
            tool_name=tool_name
        )