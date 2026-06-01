"""
评测数据集生成器 v4.0
按照意图体系完整覆盖，生成1000条样本
"""
import json
import random

# ============================================================
# 完整意图体系定义
# ============================================================

INTENT_TAXONOMY = {
    # 一、信息查询类 (INFO) - 25%
    "INFO_ACC": {
        "info_acc_balance": "余额查询 - 卡里还有多少钱",
        "info_acc_detail": "账户明细 - 交易流水、记录",
        "info_acc_status": "账户状态 - 卡状态、是否正常",
        "info_acc_info": "账户信息 - 开户行、卡号",
    },
    "INFO_BILL": {
        "info_bill_amount": "账单金额 - 欠了多少钱、本期账单",
        "info_bill_date": "还款日期 - 几号还款、截止日期",
        "info_bill_min": "最低还款 - 最少还多少",
        "info_bill_point": "积分查询 - 积分多少、怎么用",
    },
    "INFO_TRAN": {
        "info_tran_record": "交易记录 - 查询消费明细",
        "info_tran_status": "交易状态 - 某笔交易情况",
    },
    "INFO_PROD": {
        "info_prod_wealth": "理财信息 - 产品收益",
        "info_prod_loan": "贷款信息 - 利率额度",
        "info_prod_credit": "信用卡信息 - 额度年费",
    },
    "INFO_BRANCH": {
        "info_branch": "网点查询 - 在哪、地址",
        "info_phone": "电话查询 - 客服电话",
        "info_hour": "营业时间 - 几点开门",
    },
    "INFO_PROG": {
        "info_prog_application": "申请进度 - 业务审批",
        "info_prog_transfer": "转账进度 - 到账时间",
    },

    # 二、业务办理类 (BIZ) - 20%
    "BIZ_TRAN": {
        "biz_tran_internal": "行内转账 - 招行互转",
        "biz_tran_external": "跨行转账 - 转其他银行",
        "biz_tran_limit": "转账限额 - 日限额多少",
    },
    "BIZ_CARD": {
        "biz_card_loss": "卡片挂失 - 卡丢了",
        "biz_card_activate": "卡片激活 - 开卡",
        "biz_card_reissue": "补办新卡 - 换卡",
        "biz_card_cancel": "注销卡片 - 销卡",
    },
    "BIZ_PWD": {
        "biz_pwd_reset": "密码重置 - 忘记密码",
        "biz_pwd_change": "密码修改 - 改密码",
    },
    "BIZ_PAY": {
        "biz_pay_repay": "主动还款 - 还信用卡",
        "biz_pay_autopay": "自动还款 - 设置自动扣",
    },
    "BIZ_INSTALL": {
        "biz_installment": "分期办理 - 账单分期",
    },

    # 三、咨询投诉类 (CONSULT) - 20%
    "CONS_PROD": {
        "cons_prod_wealth": "理财咨询 - 产品收益风险",
        "cons_prod_loan": "贷款咨询 - 利率条件额度",
        "cons_prod_credit": "信用卡咨询 - 额度年费",
    },
    "CONS_FEE": {
        "cons_fee_tran": "转账手续费 - 跨行费",
        "cons_fee_withdrw": "取现手续费 - 提现费",
        "cons_fee_install": "分期手续费 - 分期利率",
    },
    "CONS_COMP": {
        "cons_comp_service": "服务投诉 - 态度差",
        "cons_comp_delay": "延误投诉 - 处理慢",
    },
    "CONS_URG": {
        "cons_urg_human": "转人工 - 找客服",
        "cons_urg_loss": "资金损失 - 钱被骗了",
    },

    # 四、营销推广类 (SALES) - 10%
    "SALES_WEALTH": {
        "sales_wealth_prod": "理财产品推荐",
    },
    "SALES_LOAN": {
        "sales_loan_prod": "贷款产品推荐",
        "sales_loan_rate": "贷款利率咨询",
    },
    "SALES_CREDIT": {
        "sales_credit_prod": "信用卡推荐 - 办卡",
        "sales_credit_point": "积分活动 - 打折优惠",
    },

    # 五、安全风控类 (SECURITY) - 15% [全部P0]
    "SEC_FRAUD": {
        "sec_fraud_report": "诈骗举报 - 被骗了",
        "sec_fraud_suspect": "可疑交易 - 陌生消费",
    },
    "SEC_STOLEN": {
        "sec_stolen_card": "卡片盗刷 - 卡被盗刷",
        "sec_stolen_info": "信息泄露 - 资料被盗",
    },
    "SEC_FREEZE": {
        "sec_freeze_unexpected": "异常冻结 - 卡被冻了",
    },

    # 六、系统交互类 (SYSTEM) - 10%
    "SYS": {
        "sys_greeting": "问候 - 你好",
        "sys_thanks": "感谢 - 谢谢",
        "sys_bye": "告别 - 再见",
        "sys_invalid": "无效输入 - 听不懂",
    },
}

# 样本模板（每种意图多个说法）
SAMPLE_TEMPLATES = {
    # INFO类
    "info_acc_balance": [
        "卡里还有多少钱",
        "余额查询",
        "我的账户还有多少",
        "查一下卡上剩多少钱",
        "账户余额多少",
    ],
    "info_bill_amount": [
        "本期账单多少",
        "欠了多少钱",
        "账单金额是多少",
        "我要还多少",
        "这个月账单",
        "信用卡欠款",
    ],
    "info_bill_date": [
        "还款日是哪天",
        "几号之前要还",
        "截止日期",
        "最晚什么时候还款",
        "还款截止日",
    ],
    "info_bill_min": [
        "最低还款多少",
        "最少要还多少钱",
        "最低还款额",
    ],
    "info_bill_point": [
        "积分有多少",
        "积分怎么用",
        "查一下积分",
        "我的积分",
    ],
    "info_tran_record": [
        "查一下交易记录",
        "最近消费明细",
        "历史交易",
        "账单明细",
    ],
    "info_branch": [
        "附近网点在哪",
        "最近的支行",
        "招行网点地址",
    ],
    "info_hour": [
        "营业时间",
        "几点开门",
        "网点几点下班",
    ],
    "info_phone": [
        "客服电话",
        "招行电话",
        "怎么联系客服",
    ],

    # BIZ类
    "biz_card_loss": [
        "卡丢了",
        "卡片丢失",
        "卡不见了",
        "要挂失",
        "银行卡丢了",
    ],
    "biz_card_activate": [
        "怎么激活卡片",
        "开卡",
        "新卡激活",
        "启用卡片",
    ],
    "biz_card_reissue": [
        "补办新卡",
        "卡坏了要换",
        "补卡",
        "换一张卡",
    ],
    "biz_card_cancel": [
        "注销卡片",
        "销卡",
        "取消银行卡",
    ],
    "biz_tran_internal": [
        "转账到招行卡",
        "行内转账",
        "招行互转",
    ],
    "biz_tran_external": [
        "跨行转账",
        "转账到别的银行",
        "转到他行",
    ],
    "biz_tran_limit": [
        "转账限额多少",
        "每日限额",
        "单笔最高多少",
    ],
    "biz_pwd_reset": [
        "忘记密码",
        "密码忘了",
        "重置密码",
    ],
    "biz_pwd_change": [
        "修改密码",
        "改密码",
        "换密码",
    ],
    "biz_pay_repay": [
        "还款",
        "还信用卡",
        "主动还款",
    ],
    "biz_pay_autopay": [
        "设置自动还款",
        "自动扣款",
        "绑定自动还款",
    ],
    "biz_installment": [
        "分期付款",
        "账单分期",
        "消费分期",
    ],

    # CONS类
    "cons_prod_wealth": [
        "理财产品怎么样",
        "理财收益多少",
        "想了解理财",
    ],
    "cons_prod_loan": [
        "贷款利率多少",
        "贷款额度多少",
        "信用贷",
    ],
    "cons_prod_credit": [
        "信用卡额度",
        "年费多少",
        "信用卡申请",
    ],
    "cons_fee_tran": [
        "转账手续费多少",
        "跨行费用",
    ],
    "cons_fee_withdrw": [
        "取现手续费",
        "提现费用",
        "ATM手续费",
    ],
    "cons_fee_install": [
        "分期手续费",
        "分期利率",
    ],
    "cons_comp_service": [
        "服务态度太差",
        "投诉",
        "态度不好",
    ],
    "cons_comp_delay": [
        "处理太慢了",
        "等了好久",
        "效率太低",
    ],
    "cons_urg_human": [
        "转人工",
        "找人工客服",
        "需要人工服务",
        "我要投诉",
    ],
    "cons_urg_loss": [
        "钱被骗了",
        "资金损失",
        "我被诈骗了",
    ],

    # SALES类
    "sales_wealth_prod": [
        "推荐理财产品",
        "有什么好理财",
        "想买理财",
    ],
    "sales_loan_prod": [
        "推荐贷款产品",
        "有什么贷款",
        "贷款推荐",
    ],
    "sales_loan_rate": [
        "贷款利率多少",
        "贷款利息",
    ],
    "sales_credit_prod": [
        "推荐信用卡",
        "办什么卡好",
        "新用户办卡",
    ],
    "sales_credit_point": [
        "积分兑换",
        "打折活动",
        "优惠活动",
    ],

    # SECURITY类
    "sec_fraud_report": [
        "我被骗了",
        "遇到诈骗",
        "举报诈骗",
    ],
    "sec_fraud_suspect": [
        "有陌生消费",
        "可疑交易",
        "账户异常",
    ],
    "sec_stolen_card": [
        "卡被盗刷",
        "卡片被盗",
        "被刷卡",
    ],
    "sec_stolen_info": [
        "信息泄露",
        "资料被盗",
        "隐私泄露",
    ],
    "sec_freeze_unexpected": [
        "卡被冻结了",
        "账户异常冻结",
        "卡不能用",
    ],

    # SYS类
    "sys_greeting": [
        "你好",
        "您好",
        "hi",
    ],
    "sys_thanks": [
        "谢谢",
        "感谢",
        "好的谢谢",
    ],
    "sys_bye": [
        "再见",
        "拜拜",
        "我走了",
    ],
    "sys_invalid": [
        "嗯",
        "啊",
        "呃",
        "听不懂",
    ],
}

# 复杂场景模板（用于扩充）
COMPLEX_TEMPLATES = [
    "{basic}，请问怎么处理",
    "{basic}，急",
    "{basic}，在线等",
    "{basic}，很久了",
    "我的{basic}",
    "问一下{basic}",
    "请问{basic}",
    "关于{basic}",
    "帮忙查一下{basic}",
    "要办理{basic}",
]


def generate_samples():
    """生成1000条样本"""
    samples = []
    sample_id = 1

    # 按意图分配样本数（基于重要性）
    intent_weights = {
        # INFO类 - 高频，占35%
        "info_bill_amount": 120,
        "info_acc_balance": 50,
        "info_bill_date": 40,
        "info_tran_record": 30,
        "info_branch": 25,
        "info_hour": 20,
        "info_bill_min": 15,
        "info_bill_point": 15,
        "info_phone": 10,
        "info_acc_detail": 10,
        "info_acc_status": 10,
        "info_acc_info": 5,
        "info_prod_wealth": 15,
        "info_prod_loan": 10,
        "info_prod_credit": 10,
        "info_prog_application": 10,
        "info_prog_transfer": 10,

        # BIZ类 - 高频，占30%
        "biz_card_loss": 80,
        "biz_tran_external": 50,
        "biz_tran_internal": 40,
        "biz_pay_repay": 50,
        "biz_pwd_reset": 30,
        "biz_card_activate": 25,
        "biz_card_reissue": 20,
        "biz_pwd_change": 15,
        "biz_installment": 20,
        "biz_pay_autopay": 15,
        "biz_tran_limit": 15,
        "biz_card_cancel": 10,

        # CONSULT类 - 重要，占20%
        "cons_prod_loan": 40,
        "cons_prod_credit": 40,
        "cons_prod_wealth": 30,
        "cons_urg_human": 50,
        "cons_urg_loss": 20,
        "cons_comp_service": 25,
        "cons_comp_delay": 15,
        "cons_fee_tran": 20,
        "cons_fee_withdrw": 15,
        "cons_fee_install": 15,

        # SECURITY类 - P0优先，占10%
        "sec_fraud_report": 40,
        "sec_stolen_card": 30,
        "sec_fraud_suspect": 25,
        "sec_stolen_info": 15,
        "sec_freeze_unexpected": 20,

        # SALES类 - 次要，占5%
        "sales_wealth_prod": 20,
        "sales_loan_prod": 20,
        "sales_loan_rate": 10,
        "sales_credit_prod": 15,
        "sales_credit_point": 15,

        # SYS类 - 兜底，占5%
        "sys_greeting": 40,
        "sys_thanks": 20,
        "sys_bye": 20,
        "sys_invalid": 20,
    }

    # 生成样本
    for intent, count in intent_weights.items():
        templates = SAMPLE_TEMPLATES.get(intent, [])
        if not templates:
            templates = ["查询" + intent.replace("_", "")]

        for i in range(count):
            # 基本问法
            base_template = templates[i % len(templates)]

            # 扩展场景（部分样本用复杂问法）
            if i >= len(templates) // 2 and random.random() < 0.3:
                complex_tpl = random.choice(COMPLEX_TEMPLATES)
                question = complex_tpl.format(basic=base_template)
            else:
                question = base_template

            # 判断P0
            is_p0 = intent.startswith("sec_") or intent in [
                "cons_urg_human", "cons_urg_loss", "cons_comp_service",
                "cons_comp_delay", "cons_comp_error"
            ]

            # 判断是否需要风险提示
            needs_disclosure = intent.startswith(("cons_prod", "sales_"))

            sample = {
                "id": f"SMART_{sample_id:04d}",
                "category": intent.split("_")[0].upper(),
                "sub_category": intent,
                "intent": intent,
                "expected_intent": intent,
                "question": question,
                "is_p0": is_p0,
                "required_disclosure": needs_disclosure,
            }
            samples.append(sample)
            sample_id += 1

    # 打乱顺序
    random.shuffle(samples)

    return samples


def main():
    print("生成评测数据集 v4.0...")
    samples = generate_samples()

    print(f"生成了 {len(samples)} 条样本")

    # 统计
    intent_counts = {}
    for s in samples:
        intent = s["intent"]
        intent_counts[intent] = intent_counts.get(intent, 0) + 1

    print(f"覆盖 {len(intent_counts)} 种意图")
    print()

    # 统计各类别
    category_counts = {}
    for s in samples:
        cat = s["category"]
        category_counts[cat] = category_counts.get(cat, 0) + 1

    print("类别分布:")
    for cat, count in sorted(category_counts.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")

    print()

    # 保存
    dataset = {
        "dataset_version": "v4.0",
        "total_samples": len(samples),
        "generated_date": "2026-06-01",
        "description": "招行智能客服评测数据集v4.0 - 完整覆盖60+意图类型",
        "intent_count": len(intent_counts),
        "samples": samples
    }

    output_path = "data/evaluation_dataset_v4.0.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    print(f"已保存到 {output_path}")


if __name__ == "__main__":
    main()