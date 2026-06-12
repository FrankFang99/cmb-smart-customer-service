"""
v3.4.0-b 知识库分类管理
========================

将扁平 KNOWLEDGE_BASE 拆分为 3 类:
- doc_kb    非结构化文档库 (信用卡手册 / 业务规章 / 利率表)
- faq_kb    FAQ QA 对库 (consult/marketing 类的精简问答)
- biz_db    业务数据库 mock (订单/产品/物流, Text2SQL/API 调用)

设计原则:
1. 0 依赖 (沿用 v3.4.0 风格)
2. 数据本地化 (mock 数据, 不依赖外部 API)
3. 分类清晰 (3 类 + 1 个规则库引用)
4. 易扩展 (新库只需注册)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# 导入原 KB (565 条 v2.0)
try:
    from src.rag.knowledge_base import KNOWLEDGE_BASE
except ImportError:
    KNOWLEDGE_BASE = []


# ============================================================
# Chunking 策略
# ============================================================
CHUNKING_STRATEGIES = {
    "smart": "智能语义分块 (默认, 通用)",
    "by_heading": "按标题分块 (Markdown / 文档)",
    "by_row": "按行分块 (CSV / 表格)",
    "qa_pair": "按 QA 对分块 (FAQ)",
    "full_table": "整表分块 (小型参数表)",
    "by_endpoint": "按 endpoint 分块 (API 文档)",
    "by_dialogue": "按对话回合分块 (客服录音)",
}


def _classify_chunk_strategy(entry: Dict[str, Any]) -> str:
    """根据 entry 的 category / domain 推断 Chunking 策略"""
    cat = entry.get("category", "")
    domain = entry.get("domain", "")
    if cat == "consult" or cat == "marketing":
        return "qa_pair"
    if domain in ("credit_card", "investment", "loan"):
        return "by_heading"  # 信用卡/投资/贷款类多用结构化文档
    if cat == "query":
        return "by_heading"
    if cat == "risk":
        return "smart"
    if cat == "transaction":
        return "by_heading"
    return "smart"


# ============================================================
# 知识库分类器
# ============================================================
class KnowledgeBaseClassifier:
    """将扁平 KNOWLEDGE_BASE 拆分为 3 类库"""

    # 哪些 category 算 FAQ
    FAQ_CATEGORIES = {"consult", "marketing"}
    # 哪些 category 算文档库
    DOC_CATEGORIES = {"query", "risk", "service_transfer", "transaction"}
    # 哪些 domain 是业务数据库相关 (账户/信用卡/支付/生活类查询)
    BIZ_DB_DOMAINS = {"account", "credit_card", "payment", "life"}

    def __init__(self, kb: Optional[List[Dict]] = None):
        self.raw_kb = kb if kb is not None else KNOWLEDGE_BASE
        self.doc_kb: List[Dict] = []
        self.faq_kb: List[Dict] = []
        self.biz_db_entries: List[Dict] = []  # 业务数据库引用列表
        self._classify()

    def _classify(self):
        for entry in self.raw_kb:
            entry = dict(entry)  # 浅拷贝
            entry["chunk_strategy"] = _classify_chunk_strategy(entry)
            cat = entry.get("category", "")
            domain = entry.get("domain", "")
            # 业务数据库: query 类 + 业务查询类 domain
            if cat == "query" and domain in self.BIZ_DB_DOMAINS:
                self.biz_db_entries.append(entry)
            elif cat in self.FAQ_CATEGORIES:
                self.faq_kb.append(entry)
            else:
                self.doc_kb.append(entry)

    def get_by_chunk_strategy(self, strategy: str) -> List[Dict]:
        """按 chunk 策略查"""
        all_entries = self.faq_kb + self.doc_kb + self.biz_db_entries
        return [e for e in all_entries if e.get("chunk_strategy") == strategy]

    def get_by_domain(self, domain: str) -> List[Dict]:
        """按业务领域查"""
        return [e for e in self.raw_kb if e.get("domain") == domain]

    def get_faq_by_frequency(self, freq: str = "high") -> List[Dict]:
        """FAQ 按频率查"""
        return [
            e for e in self.faq_kb
            if e.get("metadata", {}).get("frequency") == freq
        ]

    def stats(self) -> Dict[str, Any]:
        """知识库分类统计"""
        chunk_counter: Dict[str, int] = {}
        domain_counter: Dict[str, int] = {}
        cat_counter: Dict[str, int] = {}
        for e in self.raw_kb:
            s = e.get("chunk_strategy", "smart")
            chunk_counter[s] = chunk_counter.get(s, 0) + 1
            d = e.get("domain", "unknown")
            domain_counter[d] = domain_counter.get(d, 0) + 1
            c = e.get("category", "unknown")
            cat_counter[c] = cat_counter.get(c, 0) + 1
        return {
            "total": len(self.raw_kb),
            "by_class": {
                "doc_kb": len(self.doc_kb),
                "faq_kb": len(self.faq_kb),
                "biz_db_entries": len(self.biz_db_entries),
            },
            "by_chunk_strategy": chunk_counter,
            "by_domain": domain_counter,
            "by_category": cat_counter,
        }


# ============================================================
# 业务数据库 mock (Text2SQL 雏形)
# ============================================================
class BizDBMock:
    """
    业务数据库 mock (招行实战 3 大类):
    - orders      订单 (信用卡账单 / 交易订单)
    - products    产品 (理财产品 / 信用卡产品 / 贷款产品)
    - logistics   物流 (卡片邮寄 / 对账单邮寄)
    """

    def __init__(self):
        # 5 个示例客户 (mock)
        self._customers = {
            "C001": {"name": "方逸之", "phone_tail": "8888", "id_tail": "1234", "vip": True},
            "C002": {"name": "张三", "phone_tail": "1234", "id_tail": "5678", "vip": False},
            "C003": {"name": "李四", "phone_tail": "5678", "id_tail": "9012", "vip": False},
            "C004": {"name": "王五", "phone_tail": "9012", "id_tail": "3456", "vip": True},
            "C005": {"name": "赵六", "phone_tail": "3456", "id_tail": "7890", "vip": False},
        }
        # 订单 (信用卡账单 + 交易订单)
        self._orders = {
            "O1001": {"customer_id": "C001", "type": "credit_bill", "amount": 12345.67, "due_date": "2026-07-05", "status": "待还款"},
            "O1002": {"customer_id": "C001", "type": "transaction", "amount": 500.00, "merchant": "星巴克", "date": "2026-06-10", "status": "已完成"},
            "O1003": {"customer_id": "C002", "type": "credit_bill", "amount": 8888.88, "due_date": "2026-07-15", "status": "待还款"},
            "O1004": {"customer_id": "C003", "type": "credit_bill", "amount": 500.50, "due_date": "2026-06-30", "status": "已逾期"},
        }
        # 产品
        self._products = {
            "P_CMBC_CREDIT_001": {
                "name": "招商银行 Young 卡", "type": "credit_card", "annual_fee": 0,
                "cash_advance_rate": "0.05%/日", "installment_rate": "0.75%/月",
                "target": "年轻人, 首卡推荐"
            },
            "P_CMBC_CREDIT_002": {
                "name": "招商银行 标准信用卡", "type": "credit_card", "annual_fee": 100,
                "cash_advance_rate": "0.05%/日", "installment_rate": "0.75%/月",
                "target": "通用"
            },
            "P_CMBC_LOAN_001": {
                "name": "招行信用贷", "type": "loan", "max_amount": 500000,
                "annual_rate": "3.85%-12.0%", "term": "12-60期", "target": "工薪族"
            },
            "P_CMBC_WEALTH_001": {
                "name": "朝朝宝", "type": "wealth", "min_amount": 1,
                "expected_annual_return": "1.8%-2.5%", "risk_level": "R1 极低", "target": "活期理财"
            },
            "P_CMBC_WEALTH_002": {
                "name": "日日盈", "type": "wealth", "min_amount": 1000,
                "expected_annual_return": "2.5%-3.2%", "risk_level": "R2 低", "target": "短期理财"
            },
        }
        # 物流
        self._logistics = {
            "L2001": {"customer_id": "C001", "type": "card_delivery", "carrier": "顺丰", "tracking_no": "SF1234567890", "status": "在途", "eta": "2026-06-13"},
            "L2002": {"customer_id": "C002", "type": "statement_delivery", "carrier": "EMS", "tracking_no": "EMS9876543210", "status": "已签收", "eta": "2026-06-08"},
        }

    # ============================================================
    # 查询接口 (Text2SQL 雏形 - 自然语言 -> 字典查询)
    # ============================================================
    def query_bill_amount(self, customer_id: str) -> Optional[Dict]:
        """查询客户信用卡账单金额 (Text2SQL: SELECT amount, due_date FROM orders WHERE customer_id=? AND type='credit_bill')"""
        for o in self._orders.values():
            if o["customer_id"] == customer_id and o["type"] == "credit_bill":
                customer = self._customers.get(customer_id, {})
                return {
                    "amount": o["amount"],
                    "due_date": o["due_date"],
                    "status": o["status"],
                    "customer_name": customer.get("name", "客户"),
                }
        return None

    def query_transaction_record(self, customer_id: str, limit: int = 5) -> List[Dict]:
        """查询客户交易记录 (Text2SQL: SELECT * FROM orders WHERE customer_id=? AND type='transaction' ORDER BY date DESC LIMIT ?)"""
        records = [
            {"amount": o["amount"], "merchant": o.get("merchant", "-"), "date": o["date"]}
            for o in self._orders.values()
            if o["customer_id"] == customer_id and o["type"] == "transaction"
        ]
        return records[:limit]

    def query_logistics(self, customer_id: str) -> Optional[Dict]:
        """查询客户物流 (卡片邮寄/对账单邮寄)"""
        for l in self._logistics.values():
            if l["customer_id"] == customer_id:
                return l
        return None

    def query_product(self, product_id: str) -> Optional[Dict]:
        """查询产品详情"""
        return self._products.get(product_id)

    def query_credit_cards(self) -> List[Dict]:
        """查询所有信用卡产品 (Text2SQL: SELECT * FROM products WHERE type='credit_card')"""
        return [
            {"id": pid, **p}
            for pid, p in self._products.items()
            if p["type"] == "credit_card"
        ]

    def query_wealth_products(self) -> List[Dict]:
        """查询所有理财产品 (Text2SQL: SELECT * FROM products WHERE type='wealth')"""
        return [
            {"id": pid, **p}
            for pid, p in self._products.items()
            if p["type"] == "wealth"
        ]

    def format_bill_answer(self, customer_id: str) -> str:
        """格式化账单回答 (LLM 模板 + 数据)"""
        bill = self.query_bill_amount(customer_id)
        if bill is None:
            return "抱歉，未查询到您的账单信息。请确认您是否绑定该客户号。"
        return (
            f"您本期账单金额为 {bill['amount']:.2f} 元，"
            f"最后还款日为 {bill['due_date']}，"
            f"当前状态: {bill['status']}。"
            f"建议您在还款日前还清欠款，"
            f"如有疑问可拨打 95555。"
        )

    def format_logistics_answer(self, customer_id: str) -> str:
        """格式化物流回答"""
        log = self.query_logistics(customer_id)
        if log is None:
            return "抱歉，未查询到您的物流信息。"
        return (
            f"您的 {log['type']} 物流状态: {log['status']}，"
            f"快递公司: {log['carrier']}，"
            f"快递单号: {log['tracking_no']}，"
            f"预计送达: {log['eta']}。"
        )


# ============================================================
# 工厂: 统一入口
# ============================================================
def get_classifier(kb: Optional[List[Dict]] = None) -> KnowledgeBaseClassifier:
    """获取知识库分类器"""
    return KnowledgeBaseClassifier(kb)


def get_biz_db() -> BizDBMock:
    """获取业务数据库 mock"""
    return BizDBMock()
