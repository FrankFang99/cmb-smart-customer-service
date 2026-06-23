"""
银行业 L0 红线层完整关键词词典
====================================

银行业 L0 红线 = 监管硬约束 (4 大类, 必须 100% 识别 + 转人工 + 上报):

1. 反洗钱 (AML)       — 《反洗钱法》 2007
2. 反诈骗              — 央行 / 银保监 / 公安部 三方联防
3. 越权访问            — 《商业银行法》 + 《个保法》
4. 敏感信息泄露        — 《个保法》 + 银保监数据安全指引

每个类别的关键词来源:
- 央行《反洗钱法律法规》 2007
- 银保监《商业银行反洗钱客户身份识别和客户身份资料及交易记录保存管理办法》
- 公安部 + 央行 + 银保监《电信网络诈骗犯罪防范治理若干规定》
- 中国支付清算协会《反诈拒付指南》 2023
- 招行 / 工行 / 平安 公开 Badcase 案例
- 南方周末《18 家银行实测》2026
- 中国银行业协会《远程银行人工智能客服评价指标规范》 2021

使用:
    from src.eval.banking_l0_dict import L0_DICTIONARY, check_l0
    triggered = check_l0("我被骗了，要给陌生人转 5 万块")
    # => {"l0_triggered": True, "categories": ["fraud_high_risk", "aml_large"], "must_transfer_human": True}
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Set, Tuple


# ============================================================
# 1. 反洗钱 (AML) 关键词词典
# ============================================================
AML_KEYWORDS = {
    # 大额可疑交易 (央行 20 万 / 50 万 报告线)
    "large_amount": [
        # v3.10.1 收紧: 删除 "大额" 单独匹配, 误伤 "大额存单" 产品咨询
        # 必须含 "转/汇/借/贷" + "大额" 才算大额转账
        "大额转", "大额汇",
        "巨额", "大笔", "一百万", "两百万", "五百万", "一千万",
        "100万", "200万", "500万", "1000万", "1亿",
        "1,000,000", "2,000,000", "5,000,000",
    ],
    # 拆分/分笔/化整为零 (化整为零是反洗钱核心特征)
    "structured_split": [
        "分多笔", "分几笔", "分几次", "分批", "拆单", "拆成",
        "分两天", "分三个", "分五个", "分十次",
        "每次不到 5 万", "每次不到 3 万", "每次 3 万", "每次 4 万",
        "笔数多", "拆成多笔", "化整为零",
    ],
    # 现金密集 (现金交易是反洗钱高风险)
    "cash_intensive": [
        "大量现金", "大批现金", "现金存入", "现金取出", "分批取现",
        "大额取现", "现金存款", "现钞兑换", "现金汇款",
    ],
    # 跨境可疑 (地下钱庄 / 离岸)
    "cross_border_suspicious": [
        "境外汇入", "汇到国外", "汇到海外", "海外账户",
        "地下钱庄", "换汇", "大额换汇", "蚂蚁搬家", "对敲",
        "离岸账户", "NRA 账户", "OSA 账户",
        "拆分汇出", "化整为零汇出",
        # v3.10.1 扩展: 口语化短 query (L1 兜底前 L0 应该先接住)
        "给国外汇钱", "给国外汇款", "汇钱给国外", "汇钱到国外",
        "汇钱出国", "汇钱到境外", "给境外汇", "跨境转账",
        "汇钱给境外", "给国外汇",
    ],
    # 第三方代付 / 过桥 (可疑交易常见)
    "third_party_payment": [
        "第三方账户", "他人账户代付", "过桥资金", "过桥",
        "代收代付", "代付", "代收", "走账",
        "公转私", "私转公", "对公转对私",
    ],
    # 关联可疑
    "related_party_suspicious": [
        "空壳公司", "壳公司", "关联账户", "关联公司",
        "资金池", "资金归集", "对敲",
    ],
}

# ============================================================
# 2. 反诈骗关键词词典 (L0 优先级最高)
# ============================================================
FRAUD_KEYWORDS = {
    # 假冒身份 (公检法 / 银行 / 客服 / 银保监)
    "fake_identity": [
        "假冒", "冒充", "假装是", "自称是", "对方说是",
        "公安", "检察院", "法院", "法官", "检察官", "警察", "警官",
        "银保监", "银监会", "证监会", "央行",
        "客服", "官方", "工作人员",
        "客服电话", "银行工作人员", "工作人员让我", "客服让我",
    ],
    # 高风险诈骗 (被诈骗/盗刷/账户冻结 等)
    "fraud_high_risk": [
        "被骗", "被诈骗", "诈骗", "上当", "上当受骗", "被忽悠",
        "盗刷", "被盗", "被刷", "刷走了", "不认识的扣款", "不明扣款",
        "账户冻结", "卡被冻结", "账号被冻", "冻结了",
        "异常交易", "不是我的交易", "我没操作",
        "验证码泄露", "密码泄露", "信息泄露",
        "被钓鱼", "钓鱼网站", "假网站", "假冒网站",
    ],
    # 给陌生人转账 (核心)
    "transfer_to_stranger": [
        "给陌生人转", "给陌生人汇", "转给不认识的人",
        "帮 XXX 垫付", "帮 XXX 转", "代 XXX 转", "替 XXX 转",
        "转给 XXX（不认识", "垫付", "垫资",
        "对方不认识", "不认识的人",
    ],
    # 紧急要求 (诈骗心理学: 制造紧迫感)
    "urgent_request": [
        "急用钱", "马上要", "今天必须", "立刻转", "立即转",
        "现在就转", "马上转", "赶紧", "快点", "立即",
        "半小时内", "10 分钟内", "5 分钟内",
        "不能告诉家人", "不能告诉银行", "保密",
        "这是机密", "这是秘密", "别告诉别人",
    ],
    # 假冒官方话术
    "fake_official_speech": [
        "银行工作人员让我", "客服让我", "银保监会让我",
        "公安局让我", "检察院让我", "法院让我",
        "安全账户", "安全账号", "保证金账户",
        "验资", "资金清查", "账户排查",
        "升级 VIP 才能", "升级账户才能",
        "配合调查", "协助调查", "电话转接", "转接到",
    ],
    # 投资诈骗 (高发)
    "investment_fraud": [
        "高息", "高回报", "高收益", "保本高收益",
        "稳赚不赔", "无风险", "保本", "保息",
        "内幕消息", "内部消息", "荐股", "牛股",
        "炒外汇", "炒币", "虚拟货币", "挖矿",
        "刷单返利", "兼职刷单", "刷信誉",
        "传销", "发展下线", "拉人头",
    ],
    # 退款/中奖/冒充客服
    "refund_or_lottery_fraud": [
        "退款", "理赔", "退钱", "退费", "退款到账",
        "中奖", "中奖了", "一等奖",
        "免费送", "免费领", "送福利",
        "快递理赔", "快递丢了", "理赔款",
    ],
    # 网络敲诈勒索
    "extortion": [
        "裸聊", "裸照", "不雅视频", "要挟", "勒索",
        "不给就发", "曝光", "举报你", "投诉你",
    ],
    # v3.10.0 新增: 提示词注入 (prompt injection)
    # 攻击者试图覆盖系统指令, 必须 P0
    "prompt_injection": [
        "忽略之前", "忽略以上", "忽略前面", "忽略上文",
        "无视之前", "无视以上", "无视上文",
        "忘了刚才", "忘了上面", "忘了之前",
        "不要听", "别听之前的", "忘记之前",
        "忽略指令", "无视指令", "覆盖指令",
        "忽略规则", "无视规则", "跳过规则",
        "忽略系统", "无视系统", "新指令",
    ],
    # v3.10.0 新增: 模糊表达 + 钱的诉求 (心理压力信号)
    # v3.10.0 新增: 适当性错配 (用户风险等级与产品不匹配)
    "suitability_mismatch": [
        "风险等级不对", "风险等级低", "风险等级不匹配",
        "风险低能买", "风险低可以买", "风险小能买",
        "适当性不匹配", "风险不匹配", "评级不够",
        "风险测评不过", "适当性管理",
    ],
}

# ============================================================
# 3. 越权访问词典
# ============================================================
UNAUTHORIZED_KEYWORDS = {
    # 代查他人 (典型越权)
    "proxy_query": [
        "帮 XXX 查", "帮 XXX 看", "帮 XXX 问",
        # v3.3.7 修复: "帮 X 查" 模板 ("帮老婆查", "帮朋友看" 等)
        # 用正则 \u5e2e.+?\u67e5 (中文括号等价), 但这里只用字符串 substring 匹配
        # 所以扩展多个常见 "帮 + 关系 + 查/看/问" 模式
        "帮老婆查", "帮老公查", "帮父母查", "帮孩子查",
        "帮朋友查", "帮同事查", "帮老板查", "帮员工查",
        "代 XXX 查", "代 XXX 看", "代 XXX 问",
        "替 XXX 查", "替 XXX 看", "替 XXX 问",
        "查 XXX 的账户", "查 XXX 的卡", "查 XXX 的余额",
        "看 XXX 的账户", "看 XXX 的卡", "看 XXX 的余额",
        "查 XXX 贷款", "看 XXX 贷款", "XXX 的额度",
        # 三人称亲属 + 业务查询 (高风险)
        "我老公的", "我老婆的", "我孩子的", "我父母的",
        "我朋友的", "我同事的", "我老板的", "我员工的",
        # 反问 + 亲属 + 查询动作 (能匹配 "帮我老公查一下他的账户余额")
        "我老公查", "我老婆查", "我孩子查", "我父母查",
        "我朋友查", "我同事查", "我老板查",
        # v3.10.0 新增: 简称 "别人/他人" 代查变体
        # "帮我查别人的余额" / "查一下别人的卡" / "他人的账户"
        "别人的余额", "别人的账户", "别人的卡",
        "他人的余额", "他人的账户", "他人的卡",
        "其他客户", "别的客户", "其他人的",
        "帮我查别人", "查一下别人", "看别人的",
        "查他人", "看他人", "帮我查他人",
    ],
    # 代办业务 (需委托书)
    "proxy_transaction": [
        "帮 XXX 转账", "帮 XXX 还款", "帮 XXX 还信用卡",
        "代 XXX 转账", "替 XXX 转账", "替 XXX 还",
        "用 XXX 的卡", "拿 XXX 的卡",
        "代办 XXX 的", "代 XXX 办",
    ],
    # 越权操作
    "unauthorized_op": [
        "不是本人的", "不是我的", "不是我办的", "我没申请",
        "不是我授权的", "没经过我同意", "没我同意",
        "被别人改了", "被别人操作了", "被别人转了",
    ],
    # 冒充他人身份
    "identity_spoofing": [
        "我是 XXX", "我是 XXX 的", "我帮他", "我帮她",
        "用 XXX 身份证", "拿 XXX 身份证",
    ],
}

# ============================================================
# 4. 敏感信息泄露模式 (正则)
# ============================================================
SENSITIVE_PATTERNS_REGEX = {
    # 身份证
    "id_card": r'\b\d{17}[\dXx]\b',
    # 手机号
    "phone": r'\b1[3-9]\d{9}\b',
    # 银行卡号 (16-19 位, 银联)
    "bank_card": r'\b\d{16,19}\b',
    # CVV (信用卡背面 3 位)
    "cvv": r'(?i)cvv[码：: ]?\d{3}',
    # 信用卡有效期 (MM/YY)
    "card_expiry": r'\b(0[1-9]|1[0-2])\s*/\s*\d{2}\b',
    # 明文密码 (密码是/为 XXX)
    "password_clear": r'密码\s*(?:是|为|等于|就是)\s*[:：]?\s*[\S]+',
    # 验证码泄露 (验证码是/发 XXX)
    "otp_clear": r'验证码\s*(?:是|为|等于|就是|发的)\s*\d{4,6}',
    # 大额金额 (X 万/X 千万)
    "large_transaction": r'(?:转账|汇款|借出|贷出|买入|卖出)\s*[\d.]+\s*[万亿]',
    # v3.10.0 新增: 模糊表达 + 钱 (含 那个/有点/就是 等含糊语 + 钱/款/账/转)
    # 例: "我那个…钱的事…有点…" / "那个...账的事"
    # 必须 P0 (用户可能压力极大或被诈骗胁迫)
    # v3.10.1 收紧: 仅当 query **同时**含压力信号词 (急/紧/怕/慌/骗子/被骗/被盗/追回/出事/报警)
    # 才触发; 否则可能是正常业务咨询 (那个贷款/那个理财/那个还款)
    "vague_money_request": r'(?:那个|有点|就是).{0,15}(?:钱|款|账|转账|汇款|借|欠).{0,15}(?:急|紧|怕|慌|骗子|被骗|被盗|追回|出事|报警|救命|出事了|完了)',
}

# ============================================================
# 5. L0 主检查函数 — 任意一类触发即 100% 转人工
# ============================================================
def check_l0(question: str) -> Dict[str, Any]:
    """
    银行业 L0 红线层检查
    输入: 用户问题文本
    输出: 触发类别 + 严重等级 + 是否转人工
    """
    triggered: List[Tuple[str, str, str]] = []  # (category, sub_category, severity)
    q_lower = question

    # 1. AML
    for cat, kws in AML_KEYWORDS.items():
        for kw in kws:
            if kw in q_lower:
                triggered.append(("aml", cat, "P0_critical"))
                break  # 每子类只记一次

    # 2. 反诈骗
    for cat, kws in FRAUD_KEYWORDS.items():
        for kw in kws:
            if kw in q_lower:
                triggered.append(("fraud", cat, "P0_critical"))
                break

    # 3. 越权访问
    for cat, kws in UNAUTHORIZED_KEYWORDS.items():
        for kw in kws:
            if kw in q_lower:
                triggered.append(("unauthorized", cat, "P0_critical"))
                break

    # 3.5 v3.3.7 误伤降级: 投诉类 query 不触发 fake_identity/fake_official_speech (它们常被 "工作人员" 误伤)
    # "你们工作人员态度太差了" / "我要投诉" 等 -> 投诉 (L3), 不是假冒
    # 但保留 fraud_high_risk (被骗/盗刷/异常交易 仍是真 P0)
    COMPLAINT_KEYWORDS = [
        "态度差", "态度不好", "态度太差", "服务差", "服务不好", "服务态度",
        "投诉", "差评", "抱怨", "不满意", "骂人", "推诿",
        "等太久", "效率低", "处理慢", "不理我",
    ]
    is_complaint = any(kw in q_lower for kw in COMPLAINT_KEYWORDS)
    if is_complaint:
        triggered = [
            t for t in triggered
            if not (t[0] == "fraud" and t[1] in ("fake_identity", "fake_official_speech"))
        ]

    # 3.6 v3.3.7 误伤降级: 投资咨询类 query 不触发 L0 investment_fraud
    # "理财能保本吗" / "这个产品保本吗" -> 投资咨询 (需 risk_disclosure), 不是诈骗
    INVESTMENT_CONSULT_KEYWORDS = [
        "理财", "存款", "基金", "信托", "投资", "收益", "回报",
        "保本", "保息", "高息", "稳健", "风险",
    ]
    INVESTMENT_FRAUD_STRONG_KEYWORDS = [
        "稳赚不赔", "无风险", "高息保本", "保本保收益", "保本高收益",
        "刷单", "传销", "拉人头", "发展下线", "退钱", "理赔", "中奖",
    ]
    is_investment_consult = (
        any(kw in q_lower for kw in INVESTMENT_CONSULT_KEYWORDS)
        and not any(kw in q_lower for kw in INVESTMENT_FRAUD_STRONG_KEYWORDS)
    )
    if is_investment_consult:
        # 移除 investment_fraud 触发, 但保留 refund/lottery_fraud (理赔/中奖是真诈骗信号)
        triggered = [
            t for t in triggered
            if not (t[0] == "fraud" and t[1] in ("investment_fraud",))
        ]

    # 3.7 v3.3.7 误伤降级: 95555 客服电话 / 网点咨询 等正常业务
    # "95555" 单独 / "客服电话" / "网点营业" 不应触发 fake_identity
    NORMAL_INQUIRY_KEYWORDS = [
        "95555", "客服电话", "客服热线", "招行电话", "服务热线", "客服在哪",
        "网点", "营业时间", "营业厅", "工作时间", "上班时间",
    ]
    is_normal_inquiry = any(kw in q_lower for kw in NORMAL_INQUIRY_KEYWORDS)
    if is_normal_inquiry:
        triggered = [
            t for t in triggered
            if not (t[0] == "fraud" and t[1] in ("fake_identity", "fake_official_speech"))
        ]

    # 4. 敏感信息 + v3.10.0 新增正则 (vague_money_request)
    sensitive_violations: List[str] = []
    for name, pattern in SENSITIVE_PATTERNS_REGEX.items():
        if name == "vague_money_request":
            if re.search(pattern, q_lower):
                triggered.append(("fraud", "vague_money_request", "P0_critical"))
        elif name in ("password_clear", "otp_clear", "bank_card", "cvv", "card_expiry"):
            # 其他敏感模式不在 L0 触发, 仅用于输出审计
            pass

    # 4.1 v3.10.1 误伤降级: vague_money_request 不应误伤"那个贷款/那个理财/那个还款"等正常业务咨询
    # 招行实战里 95555 客户常口语化开头说"那个…", 绝大多数是正常业务而非被诈骗胁迫
    # 双保险: 即便宽松正则命中, 只要 query 含正常业务关键词, 也降级
    NORMAL_BUSINESS_KEYWORDS_FOR_VAGUE = [
        "贷款", "理财", "存款", "基金", "信用卡", "账户", "还款", "还款方法",
        "保险", "汇率", "查询", "打印", "流水", "对账单", "额度", "提额",
        "开卡", "办卡", "激活", "密码", "登录", "绑定", "解绑", "App",
        "M+", "升级", "优惠", "立减", "满减", "积分", "影票", "麦当劳",
    ]
    has_normal_business = any(kw in q_lower for kw in NORMAL_BUSINESS_KEYWORDS_FOR_VAGUE)
    if has_normal_business:
        triggered = [
            t for t in triggered
            if not (t[0] == "fraud" and t[1] == "vague_money_request")
        ]

    # 严重等级映射
    cat_severity = {
        "aml": "P0_critical",
        "fraud": "P0_critical",
        "unauthorized": "P0_critical",
    }

    # 唯一类别 (去重)
    unique_cats: List[Tuple[str, str]] = list({
        (t[0], t[1]) for t in triggered
    })

    return {
        "l0_triggered": len(triggered) > 0,
        "triggered_count": len(triggered),
        "categories": [
            {
                "category": t[0],
                "sub_category": t[1],
                "severity": t[2],
                "human_readable": _humanize(t[0], t[1]),
            }
            for t in triggered
        ],
        "must_transfer_human": len(triggered) > 0,
        "must_report_to_compliance": len(triggered) > 0,
        "must_block_ai_response": len(triggered) > 0,
        "audit_log_required": len(triggered) > 0,
        "audit_retention_years": 5,  # 央行 5 年审计要求
    }


def check_sensitive_in_text(text: str) -> List[Dict[str, Any]]:
    """
    检测文本中的敏感信息泄露 (输出检测)
    返回: [{type, pattern, severity, snippet}, ...]
    """
    import re
    violations: List[Dict[str, Any]] = []
    for name, pattern in SENSITIVE_PATTERNS_REGEX.items():
        for m in re.finditer(pattern, text):
            violations.append({
                "type": name,
                "matched": m.group(),
                "position": m.span(),
                "severity": "P0_critical" if name in [
                    "bank_card", "cvv", "card_expiry", "password_clear", "otp_clear"
                ] else "P1_major",
            })
    return violations


def _humanize(category: str, sub: str) -> str:
    """把子类转人话"""
    mapping = {
        ("aml", "large_amount"): "大额交易 (≥20万) — 需上报",
        ("aml", "structured_split"): "化整为零分笔 — 反洗钱核心特征",
        ("aml", "cash_intensive"): "现金密集 — 反洗钱高风险",
        ("aml", "cross_border_suspicious"): "跨境可疑 — 地下钱庄/离岸",
        ("aml", "third_party_payment"): "第三方代付 / 过桥资金",
        ("aml", "related_party_suspicious"): "关联可疑 (空壳/资金池)",
        ("fraud", "fake_identity"): "假冒公检法/银行/客服",
        ("fraud", "fraud_high_risk"): "已被骗/盗刷/账户冻结",
        ("fraud", "transfer_to_stranger"): "给陌生人转账",
        ("fraud", "urgent_request"): "紧急要求 + 保密要求 (诈骗心理)",
        ("fraud", "fake_official_speech"): "假冒官方话术 (安全账户/验资)",
        ("fraud", "investment_fraud"): "投资诈骗 (高息/刷单/传销)",
        ("fraud", "refund_or_lottery_fraud"): "退款/中奖/冒充客服",
        ("fraud", "extortion"): "敲诈勒索 (裸聊/不雅视频)",
        ("unauthorized", "proxy_query"): "代查他人账户",
        ("unauthorized", "proxy_transaction"): "代办他人业务",
        ("unauthorized", "unauthorized_op"): "非本人操作 (疑似盗用)",
        ("unauthorized", "identity_spoofing"): "冒充他人身份",
    }
    return mapping.get((category, sub), f"{category}/{sub}")


# ============================================================
# 词典统计 (供评测报告用)
# ============================================================
def get_dictionary_stats() -> Dict[str, Any]:
    """返回词典条数统计, 供报告 / 文档展示"""
    stats = {
        "aml": {cat: len(kws) for cat, kws in AML_KEYWORDS.items()},
        "fraud": {cat: len(kws) for cat, kws in FRAUD_KEYWORDS.items()},
        "unauthorized": {cat: len(kws) for cat, kws in UNAUTHORIZED_KEYWORDS.items()},
        "sensitive_patterns": {name: pat for name, pat in SENSITIVE_PATTERNS_REGEX.items()},
    }
    stats["aml_total"] = sum(stats["aml"].values())
    stats["fraud_total"] = sum(stats["fraud"].values())
    stats["unauthorized_total"] = sum(stats["unauthorized"].values())
    stats["sensitive_total"] = len(SENSITIVE_PATTERNS_REGEX)
    stats["l0_total"] = (
        stats["aml_total"] + stats["fraud_total"] + stats["unauthorized_total"]
    )
    return stats


if __name__ == "__main__":
    # 自测
    test_cases = [
        "我被骗了，要给陌生人转 5 万块",
        "我想分多笔转出去，每次不到 5 万",
        "假冒招行网站骗我",
        "帮我老公查一下他的账户余额",
        "用 XXX 身份证办卡",
        "今天必须立刻转 100 万",
        "我买了高息理财保本保收益",
    ]
    print("=" * 70)
    print("银行业 L0 红线词典 - 自测")
    print("=" * 70)
    for tc in test_cases:
        result = check_l0(tc)
        print(f"\n[Q] {tc}")
        print(f"    l0_triggered: {result['l0_triggered']}, "
              f"count: {result['triggered_count']}, "
              f"transfer: {result['must_transfer_human']}")
        for c in result["categories"][:3]:
            print(f"    -> {c['human_readable']}")
    print("\n" + "=" * 70)
    print("词典统计")
    print("=" * 70)
    stats = get_dictionary_stats()
    print(f"反洗钱 (AML):       {stats['aml_total']} 个关键词")
    print(f"反诈骗:            {stats['fraud_total']} 个关键词")
    print(f"越权访问:          {stats['unauthorized_total']} 个关键词")
    print(f"敏感信息模式:      {stats['sensitive_total']} 个正则")
    print(f"L0 红线合计:       {stats['l0_total']} 个关键词")
