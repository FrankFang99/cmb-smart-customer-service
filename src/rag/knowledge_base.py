"""
招商银行零售业务知识库
按业务分类分层组织
"""
from typing import List, Dict


# 一级分类
CATEGORIES = {
    "account": "账户与安全",
    "credit_card": "信用卡",
    "investment": "投资理财",
    "loan": "贷款业务",
    "payment": "支付结算",
    "life_service": "生活服务",
    "service": "服务与反馈",
    "security": "安全合规",
}

# 二级分类（按需扩展）
SUB_CATEGORIES = {
    "account": ["余额查询", "密码重置", "账户锁定", "身份更新"],
    "credit_card": ["账单查询", "还款方式", "卡片管理", "积分兑换"],
    "investment": ["理财产品", "基金", "黄金", "存款"],
    "loan": ["信用贷款", "房贷", "消费贷"],
    "payment": ["转账", "限额", "支付方式"],
    "life_service": ["网点查询", "ATM", "预约服务"],
    "service": ["问候", "投诉", "转人工"],
    "security": ["敏感数据", "未授权访问", "合规红线"],
}


# 知识库条目
# 格式：{id, category, question, answer, tags, metadata}
KNOWLEDGE_BASE = [
    # === 账户与安全 ===
    {
        "id": "KB_ACC_001",
        "category": "account",
        "question": "如何查询账户余额？",
        "answer": "您可以通过以下方式查询账户余额：\n1. 手机银行APP：登录后点击"我的账户"即可查看\n2. 网上银行：登录www.cmbchina.com\n3. 电话银行：拨打95555按语音提示操作\n4. 柜台查询：携带身份证到任意网点办理",
        "tags": ["余额", "查询", "账户"],
        "metadata": {"intent": "account_balance", "frequency": "high", "risk_disclosure": False}
    },
    {
        "id": "KB_ACC_002",
        "category": "account",
        "question": "忘记网银密码怎么办？",
        "answer": "您可以通过以下方式重置网银密码：\n1. 手机银行APP：登录页点击"忘记密码"，通过短信验证码重置\n2. 网上银行：点击"忘记密码"，验证身份后重置\n3. 网点办理：携带身份证到任意网点办理密码重置",
        "tags": ["密码", "忘记", "网银"],
        "metadata": {"intent": "password_reset", "frequency": "medium", "risk_disclosure": False}
    },
    {
        "id": "KB_ACC_003",
        "category": "account",
        "question": "账户被锁定了怎么办？",
        "answer": "您的账户已被锁定，请按以下步骤处理：\n1. 立即拨打95555客服热线\n2. 携带有效身份证件到就近网点\n3. 核实身份后办理解锁手续\n为保障您的账户安全，建议同时修改密码。",
        "tags": ["账户锁定", "解锁", "安全"],
        "metadata": {"intent": "account_locked", "frequency": "medium", "risk_disclosure": False, "human_transfer": True}
    },

    # === 信用卡 ===
    {
        "id": "KB_CC_001",
        "category": "credit_card",
        "question": "如何查看信用卡账单？",
        "answer": "查看信用卡账单的方式：\n1. 手机银行：登录后点击"信用卡"->"账单查询"\n2. 网上银行：登录后进入"信用卡"->"账单管理"\n3. 微信银行：关注"招商银行信用卡"公众号，绑定后查询\n4. 短信查询：发送"ZD卡号末4位"到95555",
        "tags": ["账单", "信用卡", "查询"],
        "metadata": {"intent": "bill_query", "frequency": "high", "risk_disclosure": False}
    },
    {
        "id": "KB_CC_002",
        "category": "credit_card",
        "question": "信用卡还款方式有哪些？",
        "answer": "信用卡还款方式：\n1. 自动还款：绑定借记卡每月自动扣款\n2. 手机银行还款：登录后点击"信用卡还款"\n3. 网上银行还款：登录后进入信用卡还款页面\n4. 支付宝/微信还款：在相应APP中搜索"招商银行信用卡"\n5. 柜台还款：携带信用卡到任意网点",
        "tags": ["还款", "信用卡", "方式"],
        "metadata": {"intent": "repayment_method", "frequency": "high", "risk_disclosure": False}
    },
    {
        "id": "KB_CC_003",
        "category": "credit_card",
        "question": "怎么设置自动还款？",
        "answer": "设置自动还款步骤：\n1. 打开手机银行APP\n2. 进入"信用卡"->"自动还款设置"\n3. 选择绑定的借记卡\n4. 设置还款方式（全额/最低）\n5. 确认设置\n确保借记卡余额充足，避免扣款失败。",
        "tags": ["自动还款", "绑定", "设置"],
        "metadata": {"intent": "auto_repayment", "frequency": "high", "risk_disclosure": False}
    },
    {
        "id": "KB_CC_004",
        "category": "credit_card",
        "question": "信用卡丢了怎么办？",
        "answer": "信用卡丢失后请立即挂失：\n1. 手机银行：登录后点击"信用卡"->"卡片管理"->"挂失"\n2. 网上银行：登录后进入"信用卡"->"卡片管理"->"挂失"\n3. 电话挂失：拨打95555\n4. 网点挂失：携带身份证到任意网点\n\n挂失后如需补卡，可通过上述渠道申请。挂失手续费50元/卡，新卡3-5个工作日寄出。",
        "tags": ["挂失", "丢失", "信用卡", "补卡"],
        "metadata": {"intent": "card_loss", "frequency": "high", "risk_disclosure": False}
    },
    {
        "id": "KB_CC_005",
        "category": "credit_card",
        "question": "信用卡积分怎么用？",
        "answer": "积分使用方法：\n1. 兑换礼品：进入"掌上生活"->"积分礼遇"\n2. 航空里程：积分兑换航空公司里程\n3. 刷卡抵扣：部分商户可用积分抵现\n4. 抽奖：积分参与掌上生活抽奖活动\n查询积分：在手机银行或掌上生活APP首页查看",
        "tags": ["积分", "兑换", "礼品"],
        "metadata": {"intent": "points_usage", "frequency": "high", "risk_disclosure": False}
    },

    # === 投资理财（需风险提示）===
    {
        "id": "KB_INV_001",
        "category": "investment",
        "question": "有哪些理财产品？",
        "answer": "⚠️ 理财有风险，投资需谨慎\n\n招商银行理财产品类型：\n1. 现金管理类：天天宝、朝招利等，灵活存取，1元起投\n2. 固定收益类：增利系列、安利系列，期限3个月-1年，1万起投\n3. 净值型：代销基金、保险理财等，5万起投\n4. 结构性存款：保本浮动收益\n\n您可以通过手机银行"理财"频道查看在售产品，或联系客户经理获取专属推荐。",
        "tags": ["理财", "产品", "购买"],
        "metadata": {"intent": "product_query", "frequency": "high", "risk_disclosure": True}
    },
    {
        "id": "KB_INV_002",
        "category": "investment",
        "question": "理财收益怎么算？",
        "answer": "⚠️ 历史收益不代表未来表现，投资有风险\n\n理财收益计算方式：\n1. 预期年化收益：购买金额 × 年化收益率 × 持有天数 / 365\n2. 实际收益：以产品到期实际净值为准\n3. 起息日：产品成立后开始计算收益\n4. 到期日：产品到期日次日返还本息\n\n示例：购买10万增利系列（年化4.5%），持有90天，收益=100000×4.5%×90/365≈1109元",
        "tags": ["收益", "计算", "年化"],
        "metadata": {"intent": "product_earnings", "frequency": "high", "risk_disclosure": True}
    },
    {
        "id": "KB_INV_003",
        "category": "investment",
        "question": "买基金有什么风险？",
        "answer": "⚠️ 基金非存款，市场有风险，投资需谨慎\n\n基金投资主要风险：\n1. 市场风险：基金净值随市场波动，可能亏损\n2. 信用风险：基金公司违约风险（极低）\n3. 流动性风险：赎回时可能需要等待\n\n不同类型基金风险等级：\n- 货币基金：低风险，类似于活期存款\n- 债券基金：中等风险，主要投资债券\n- 股票基金：高风险，主要投资股票\n\n请根据自身风险承受能力选择合适的产品。",
        "tags": ["基金", "风险", "亏损"],
        "metadata": {"intent": "fund_risk", "frequency": "high", "risk_disclosure": True}
    },
    {
        "id": "KB_INV_004",
        "category": "investment",
        "question": "黄金现在能买吗？",
        "answer": "⚠️ 黄金价格实时波动，投资有风险，请谨慎决策\n\n黄金投资产品类型：\n1. 黄金活期：实时交易，T+0到账，适合短线操作\n2. 账户金：投资型，低买高卖赚取差价\n3. 实物金：可提取实物金条，有收藏价值\n4. 黄金基金：门槛低，100元起投\n\n购买前请评估自身风险承受能力，关注国际金价走势。",
        "tags": ["黄金", "投资", "价格"],
        "metadata": {"intent": "gold_trading", "frequency": "high", "risk_disclosure": True}
    },
    {
        "id": "KB_INV_005",
        "category": "investment",
        "question": "存款利率是多少？",
        "answer": "招商银行人民币存款利率（参考，以实际公布为准）：\n\n活期存款：0.30%\n定期存款：\n- 3个月：1.50%\n- 6个月：1.70%\n- 1年期：1.90%\n- 2年期：2.40%\n- 3年期：2.75%\n\n大额存单（20万起存）：\n- 1年期：约2.1%\n- 3年期：约2.9%\n\n具体利率请以手机银行实际显示为准，或咨询95555。",
        "tags": ["存款", "利率", "定期"],
        "metadata": {"intent": "deposit_rate", "frequency": "high", "risk_disclosure": False}
    },

    # === 贷款业务（需风险提示）===
    {
        "id": "KB_LN_001",
        "category": "loan",
        "question": "信用贷款利率多少？",
        "answer": "⚠️ 贷款有风险，请确保按时还款，避免影响信用记录\n\n招商银行信用贷款利率（参考）：\n- 年化利率范围：4.35%-18%\n- 具体利率根据个人资质审批\n- 贷款额度：最高30万\n- 贷款期限：最长5年\n\n申请方式：手机银行APP->贷款->信用贷款\n实际利率以审批合同为准。",
        "tags": ["信用贷款", "利率", "贷款"],
        "metadata": {"intent": "credit_loan", "frequency": "high", "risk_disclosure": True}
    },
    {
        "id": "KB_LN_002",
        "category": "loan",
        "question": "房贷利率现在多少？",
        "answer": "⚠️ 房贷利率会随市场变化，以贷款合同为准\n\n当前房贷利率（参考，以实际审批为准）：\n- 首套房：LPR+0基点（约4.2%）\n- 二套房：LPR+30基点（约4.5%）\n- 具体利率根据客户资质、房屋情况而定\n\nLPR每月20日公布，请关注最新利率。\n如需了解详情，请联系客户经理或拨打95555。",
        "tags": ["房贷", "利率", "LPR"],
        "metadata": {"intent": "mortgage_rate", "frequency": "high", "risk_disclosure": True}
    },

    # === 支付结算 ===
    {
        "id": "KB_PAY_001",
        "category": "payment",
        "question": "怎么转账？",
        "answer": "转账操作步骤：\n1. 打开招商银行手机APP\n2. 点击首页"转账"\n3. 选择转账方式（同行/跨行）\n4. 输入收款人信息（姓名、卡号、开户行）\n5. 输入转账金额\n6. 确认信息并输入密码完成转账\n\n注意：转账限额单笔最高50万，日累计最高100万。",
        "tags": ["转账", "操作", "汇款"],
        "metadata": {"intent": "transfer_guide", "frequency": "high", "risk_disclosure": False}
    },
    {
        "id": "KB_PAY_002",
        "category": "payment",
        "question": "跨行转账要手续费吗？",
        "answer": "跨行转账手续费标准：\n1. 手机银行：每月前3笔免费，后续0.1%收取（最高50元）\n2. 网上银行：0.1%收取（最高50元）\n3. 柜台办理：0.2%收取（最高50元）\n4. 本行转账：免费\n\n具体手续费以APP实际显示为准。",
        "tags": ["跨行转账", "手续费", "免费"],
        "metadata": {"intent": "transfer_fee", "frequency": "high", "risk_disclosure": False}
    },
    {
        "id": "KB_PAY_003",
        "category": "payment",
        "question": "转账限额是多少？",
        "answer": "转账限额说明：\n\n手机银行：\n- 单笔最高：50万\n- 日累计最高：100万\n\n网上银行：\n- 无证书版：单笔1000，日累计5000\n- 证书版：单笔50万，日累计100万\n\n如需调整限额，可携带身份证到网点办理或咨询95555。",
        "tags": ["转账限额", "单笔", "日累计"],
        "metadata": {"intent": "transfer_limit", "frequency": "high", "risk_disclosure": False}
    },

    # === 生活服务 ===
    {
        "id": "KB_LS_001",
        "category": "life_service",
        "question": "怎么查找附近的网点？",
        "answer": "查找网点方式：\n1. 手机银行APP：首页点击"网点服务"->"网点查询"，可查看附近网点及实时排队情况\n2. 网上银行：进入"网点服务"->"网点查询"\n3. 微信银行：点击"附近网点"查询\n4. 拨打95555人工查询\n\n可查看网点地址、营业时间、电话、实时排队人数。",
        "tags": ["网点", "分行", "支行", "查找", "地址"],
        "metadata": {"intent": "branch_query", "frequency": "medium", "risk_disclosure": False}
    },
    {
        "id": "KB_LS_002",
        "category": "life_service",
        "question": "网点营业时间？",
        "answer": "网点营业时间：\n\n周一至周五：9:00-17:00\n周六周日：部分网点营业，9:00-16:00（具体以各网点为准）\n\n法定节假日：部分网点营业或休息，请提前查询\n\n查询方式：手机银行"网点服务"查看各网点具体营业时间。",
        "tags": ["营业时间", "开门", "关门"],
        "metadata": {"intent": "branch_hours", "frequency": "high", "risk_disclosure": False}
    },
    {
        "id": "KB_LS_003",
        "category": "life_service",
        "question": "可以预约网点吗？",
        "answer": "预约网点服务步骤：\n1. 打开手机银行APP\n2. 进入"网点服务"->"预约服务"\n3. 选择网点和业务类型\n4. 选择预约日期和时间\n5. 确认预约\n\n预约成功后，请按时到网点，携带身份证。\n可通过手机银行查看实时排队情况，合理安排时间。",
        "tags": ["预约", "网点", "排队"],
        "metadata": {"intent": "branch_reservation", "frequency": "high", "risk_disclosure": False}
    },

    # === 服务与反馈 ===
    {
        "id": "KB_SV_001",
        "category": "service",
        "question": "对服务不满意怎么投诉？",
        "answer": "您可以通过以下渠道反馈意见：\n1. 客服热线：拨打95555，转人工服务反馈\n2. 手机银行：进入"我的"->"意见反馈"\n3. 网上银行：登录后进入"帮助与反馈"->"意见反馈"\n4. 网点投诉：到任意网点向工作人员反馈\n\n我们会在1-3个工作日内给您回复，感谢您的反馈。",
        "tags": ["投诉", "反馈", "不满", "意见"],
        "metadata": {"intent": "complaint", "frequency": "low", "risk_disclosure": False, "human_transfer": True}
    },
]


def get_knowledge_by_category(category: str) -> List[Dict]:
    """根据分类获取知识"""
    return [item for item in KNOWLEDGE_BASE if item["category"] == category]


def get_knowledge_by_intent(intent: str) -> List[Dict]:
    """根据意图获取知识"""
    return [item for item in KNOWLEDGE_BASE if item.get("metadata", {}).get("intent") == intent]


def get_all_categories() -> List[str]:
    """获取所有一级分类"""
    return list(CATEGORIES.keys())


def needs_risk_disclosure(intent: str) -> bool:
    """判断某意图是否需要风险提示"""
    for item in KNOWLEDGE_BASE:
        if item.get("metadata", {}).get("intent") == intent:
            return item.get("metadata", {}).get("risk_disclosure", False)
    return False


def needs_human_transfer(intent: str) -> bool:
    """判断某意图是否需要转人工"""
    for item in KNOWLEDGE_BASE:
        if item.get("metadata", {}).get("intent") == intent:
            return item.get("metadata", {}).get("human_transfer", False)
    return False