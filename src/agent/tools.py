"""
妯℃嫙閾惰涓氬姟宸ュ叿
瀹為檯涓嶈繛鎺ョ湡瀹炵郴缁燂紝浠呯敤浜庢紨绀?"""
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import random


@dataclass
class ToolResult:
    """宸ュ叿鎵ц缁撴灉"""
    success: bool
    data: Any
    message: str
    tool_name: str


class BankingTools:
    """
    妯℃嫙閾惰涓氬姟宸ュ叿
    """

    @staticmethod
    def check_balance(account_id: str) -> ToolResult:
        """鏌ヨ璐︽埛浣欓锛堟ā鎷燂級"""
        # 妯℃嫙浣欓鏁版嵁
        balance = round(random.uniform(1000, 100000), 2)
        return ToolResult(
            success=True,
            data={"account_id": account_id, "balance": balance, "currency": "CNY"},
            message=f"璐︽埛 {account_id} 浣欓涓?{balance} 鍏?,
            tool_name="check_balance"
        )

    @staticmethod
    def query_bill(card_id: str, month: str = None) -> ToolResult:
        """鏌ヨ淇＄敤鍗¤处鍗曪紙妯℃嫙锛?""
        if month is None:
            from datetime import datetime
            month = datetime.now().strftime("%Y-%m")

        # 妯℃嫙璐﹀崟鏁版嵁
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
            message=f"鎮▄month}鏈堢殑璐﹀崟閲戦涓?{bill_amount} 鍏冿紝鏈€浣庤繕娆?{min_payment} 鍏冿紝鍒版湡鏃?{due_date.strftime('%Y-%m-%d')}",
            tool_name="query_bill"
        )

    @staticmethod
    def search_branch(city: str = None, district: str = None) -> ToolResult:
        """鏌ヨ閾惰缃戠偣锛堟ā鎷燂級"""
        # 妯℃嫙缃戠偣鏁版嵁
        branches = [
            {"name": "鎷涘晢閾惰浣涘北鍒嗚", "address": "浣涘北甯傜鍩庡尯绁栧簷璺?鍙?, "phone": "0757-82345678", "hours": "9:00-17:00"},
            {"name": "鎷涘晢閾惰绂呭煄鏀", "address": "浣涘北甯傜鍩庡尯瀛ｅ崕浜旇矾28鍙?, "phone": "0757-82345679", "hours": "9:00-17:00"},
            {"name": "鎷涘晢閾惰鍗楁捣鏀", "address": "浣涘北甯傚崡娴峰尯妗傚煄琛楅亾鍗楁捣澶ч亾18鍙?, "phone": "0757-86234567", "hours": "9:00-17:00"},
        ]

        if city:
            branches = [b for b in branches if city in b["name"] or city in b["address"]]

        return ToolResult(
            success=True,
            data=branches,
            message=f"鎵惧埌 {len(branches)} 涓綉鐐?,
            tool_name="search_branch"
        )

    @staticmethod
    def get_product_info(product_type: str = "all") -> ToolResult:
        """鏌ヨ浜у搧淇℃伅锛堟ā鎷燂級"""
        products = {
            "鐞嗚储": [
                {"name": "澧炲埄绯诲垪", "risk": "涓綆", "min_amount": "10000", "period": "3-12涓湀", "expected_return": "3.5%-4.5%"},
                {"name": "绋崇ǔ鐩?, "risk": "浣?, "min_amount": "5000", "period": "6涓湀", "expected_return": "3.2%-3.8%"},
            ],
            "瀛樻": [
                {"name": "澶ч瀛樺崟", "risk": "鏃?, "min_amount": "200000", "period": "1-3骞?, "expected_return": "2.1%-2.9%"},
                {"name": "瀹氭湡瀛樻", "risk": "鏃?, "min_amount": "50", "period": "3涓湀-5骞?, "expected_return": "1.5%-2.75%"},
            ],
            "璐锋": [
                {"name": "淇＄敤璐锋", "risk": "-", "min_amount": "10000", "period": "鏈€闀?骞?, "max_amount": "500000"},
                {"name": "鎴胯捶", "risk": "-", "min_amount": "100000", "period": "鏈€闀?0骞?, "max_amount": "鏃犱笂闄?},
            ]
        }

        if product_type == "all":
            return ToolResult(
                success=True,
                data=products,
                message="鎴戣涓昏浜у搧鍖呮嫭鐞嗚储銆佸瓨娆俱€佽捶娆句笁澶х被",
                tool_name="get_product_info"
            )
        else:
            return ToolResult(
                success=True,
                data=products.get(product_type, []),
                message=f"{product_type}绫讳骇鍝佷俊鎭?,
                tool_name="get_product_info"
            )

    @staticmethod
    def card_loss_report(card_id: str) -> ToolResult:
        """淇＄敤鍗℃寕澶憋紙妯℃嫙锛?""
        return ToolResult(
            success=True,
            data={"card_id": card_id, "report_time": datetime.now().isoformat(), "status": "鎸傚け鎴愬姛"},
            message=f"鎮ㄧ殑淇＄敤鍗?{card_id} 宸叉垚鍔熸寕澶憋紝鏂板崱灏嗗湪3-5涓伐浣滄棩鍐呭瘎鍑?,
            tool_name="card_loss_report"
        )

    @staticmethod
    def transfer_guide(amount: float = None, target_bank: str = None) -> ToolResult:
        """杞处鎸囧紩锛堟ā鎷燂級"""
        guide = """
杞处鎿嶄綔姝ラ锛?1. 鎵撳紑鎷涘晢閾惰鎵嬫満APP
2. 鐐瑰嚮棣栭〉"杞处"
3. 閫夋嫨"杞处鍒伴摱琛屽崱"
4. 杈撳叆鏀舵浜轰俊鎭細
   - 鏀舵浜哄鍚?   - 鏀舵鍗″彿
   - 寮€鎴烽摱琛?5. 杈撳叆杞处閲戦
6. 閫夋嫨杞处鏂瑰紡锛堝疄鏃?鏅€氾級
7. 纭淇℃伅骞惰緭鍏ュ瘑鐮佸畬鎴愯浆璐?
娉ㄦ剰浜嬮」锛?- 杞处闄愰锛氬崟绗旀渶楂?0涓囷紝鏃ョ疮璁℃渶楂?00涓?- 璺ㄨ杞处鍙兘鏀跺彇鎵嬬画璐癸紝鏍囧噯璇锋煡鐪婣PP鍐?杞处鎵嬬画璐?
- 璇锋牳瀹炴敹娆句汉淇℃伅锛岃浆璐﹀悗鏃犳硶鎾ら攢
"""

        return ToolResult(
            success=True,
            data={"guide": guide, "transfer_amount": amount, "target_bank": target_bank},
            message=guide.strip(),
            tool_name="transfer_guide"
        )

    @staticmethod
    def schedule_human_service(session_id: str, reason: str = None) -> ToolResult:
        """棰勭害浜哄伐鏈嶅姟锛堟ā鎷燂級"""
        return ToolResult(
            success=True,
            data={"session_id": session_id, "wait_time": "棰勮绛夊緟5-10鍒嗛挓", "queue_number": random.randint(1, 99)},
            message="宸蹭负鎮ㄩ绾︿汉宸ユ湇鍔★紝褰撳墠棰勮绛夊緟5-10鍒嗛挓锛岃绋嶅€?,
            tool_name="schedule_human_service"
        )


# 宸ュ叿娉ㄥ唽琛?BANKING_TOOLS = {
    "check_balance": BankingTools.check_balance,
    "query_bill": BankingTools.query_bill,
    "search_branch": BankingTools.search_branch,
    "get_product_info": BankingTools.get_product_info,
    "card_loss_report": BankingTools.card_loss_report,
    "transfer_guide": BankingTools.transfer_guide,
    "schedule_human_service": BankingTools.schedule_human_service,
}


def execute_tool(tool_name: str, **kwargs) -> ToolResult:
    """鎵ц宸ュ叿"""
    if tool_name not in BANKING_TOOLS:
        return ToolResult(
            success=False,
            data=None,
            message=f"鏈煡宸ュ叿: {tool_name}",
            tool_name=tool_name
        )

    try:
        return BANKING_TOOLS[tool_name](**kwargs)
    except Exception as e:
        return ToolResult(
            success=False,
            data=None,
            message=f"宸ュ叿鎵ц閿欒: {str(e)}",
            tool_name=tool_name
        )