"""
银行客服知识库
包含 FAQ、产品信息、网点信息等
"""
from typing import List, Dict
from dataclasses import dataclass


@dataclass
class KnowledgeItem:
    """知识条目"""
    id: str
    category: str  # 分类
    question: str   # 问题
    answer: str     # 回答
    tags: List[str]  # 标签
    metadata: Dict  # 额外信息


# 模拟银行知识库数据
KNOWLEDGE_BASE = [
    # === 账户类 ===
    {
        "id": "acc_001",
        "category": "account",
        "question": "如何查询账户余额？",
        "answer": "您可以通过以下方式查询账户余额：\n1. 手机银行APP：登录后点击"我的账户"即可查看\n2. 网上银行：登录www.cmbchina.com\n3. 电话银行：拨打95555按语音提示操作\n4. 柜台查询：携带身份证到任意网点办理",
        "tags": ["余额", "查询", "账户"],
        "metadata": {"intent": "account_query", "frequency": "high"}
    },
    {
        "id": "acc_002",
        "category": "account",
        "question": "忘记网银密码怎么办？",
        "answer": "您可以通过以下方式重置网银密码：\n1. 手机银行APP：登录页点击"忘记密码"，通过短信验证码重置\n2. 网上银行：点击"忘记密码"，验证身份后重置\n3. 网点办理：携带身份证到任意网点办理密码重置",
        "tags": ["密码", "忘记", "网银"],
        "metadata": {"intent": "account_query", "frequency": "medium"}
    },

    # === 账单类 ===
    {
        "id": "bill_001",
        "category": "bill",
        "question": "如何查看信用卡账单？",
        "answer": "查看信用卡账单的方式：\n1. 手机银行：登录后点击"信用卡"->"账单查询"\n2. 网上银行：登录后进入"信用卡"->"账单管理"\n3. 微信银行：关注"招商银行信用卡"公众号，绑定后查询\n4. 短信查询：发送"ZD卡号末4位"到95555",
        "tags": ["账单", "信用卡", "查询"],
        "metadata": {"intent": "bill_query", "frequency": "high"}
    },
    {
        "id": "bill_002",
        "category": "bill",
        "question": "信用卡还款方式有哪些？",
        "answer": "信用卡还款方式：\n1. 自动还款：绑定借记卡每月自动扣款\n2. 手机银行还款：登录后点击"信用卡还款"\n3. 网上银行还款：登录后进入信用卡还款页面\n4. 支付宝/微信还款：在相应APP中搜索"招商银行信用卡"\n5. 柜台还款：携带信用卡到任意网点",
        "tags": ["还款", "信用卡", "方式"],
        "metadata": {"intent": "bill_query", "frequency": "high"}
    },

    # === 网点类 ===
    {
        "id": "branch_001",
        "category": "branch",
        "question": "如何查找最近的招商银行网点？",
        "answer": "查找网点的方式：\n1. 手机银行APP：首页点击"网点服务"->"网点查询"，可查看附近网点及排队情况\n2. 网上银行：进入"网点服务"->"网点查询"\n3. 微信银行：点击"附近网点"查询\n4. 拨打95555人工查询",
        "tags": ["网点", "分行", "支行", "查找", "地址"],
        "metadata": {"intent": "branch_query", "frequency": "medium"}
    },

    # === 产品类 ===
    {
        "id": "prod_001",
        "category": "product",
        "question": "有哪些理财产品可以购买？",
        "answer": "招商银行理财产品类型：\n1. 现金管理类：天天宝、朝招利等，灵活存取\n2. 固定收益类：增利系列、安利系列，期限3个月-1年\n3. 净值型：代销基金、保险理财等\n4. 结构性存款：保本浮动收益\n\n您可以通过手机银行"理财"频道查看在售产品，或联系客户经理获取专属推荐。",
        "tags": ["理财", "产品", "购买"],
        "metadata": {"intent": "product_query", "frequency": "medium"}
    },

    # === 卡片管理类 ===
    {
        "id": "card_001",
        "category": "card",
        "question": "信用卡丢失怎么办？",
        "answer": "信用卡丢失后请立即挂失：\n1. 手机银行：登录后点击"信用卡"->"卡片管理"->"挂失"\n2. 网上银行：登录后进入"信用卡"->"卡片管理"->"挂失"\n3. 电话挂失：拨打95555\n4. 网点挂失：携带身份证到任意网点\n\n挂失后如需补卡，可通过上述渠道申请，我行将邮寄新卡至您指定地址。挂失手续费50元/卡。",
        "tags": ["挂失", "丢失", "信用卡", "补卡"],
        "metadata": {"intent": "card_manage", "frequency": "low"}
    },

    # === 投诉类 ===
    {
        "id": "comp_001",
        "category": "complaint",
        "question": "对服务不满意如何投诉？",
        "answer": "您可以通过以下渠道反馈意见：\n1. 客服热线：拨打95555，转人工服务反馈\n2. 手机银行：进入"我的"->"意见反馈"\n3. 网上银行：登录后进入"帮助与反馈"->"意见反馈"\n4. 网点投诉：到任意网点向工作人员反馈\n5. 信件投诉：寄至招商银行消费者权益保护中心\n\n我们会在1-3个工作日内给您回复，感谢您的反馈。",
        "tags": ["投诉", "反馈", "不满", "意见"],
        "metadata": {"intent": "complaint", "frequency": "low"}
    },

    # === 转账类 ===
    {
        "id": "trans_001",
        "category": "transfer",
        "question": "如何进行跨行转账？",
        "answer": "跨行转账方式：\n1. 手机银行：登录后点击"转账"->"跨行转账"，填写收款行信息\n2. 网上银行：登录后进入"转账汇款"->"跨行转账"\n3. 大额转账：建议使用U盾或密码器确保安全\n\n注意：跨行转账可能收取手续费，具体标准请查看手机银行"转账手续费"页面或咨询95555。",
        "tags": ["转账", "跨行", "汇款"],
        "metadata": {"intent": "transfer_guide", "frequency": "medium"}
    },
]


def get_knowledge_by_intent(intent: str) -> List[Dict]:
    """根据意图获取相关知识"""
    return [item for item in KNOWLEDGE_BASE if item.get("metadata", {}).get("intent") == intent]


def get_all_categories() -> List[str]:
    """获取所有知识分类"""
    return list(set(item["category"] for item in KNOWLEDGE_BASE))