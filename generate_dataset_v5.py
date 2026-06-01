"""
评测数据集生成器 v5.0
按照真实复杂场景 + 多意图格式生成
参考：招行95555真实咨询 + 图片评分标准
"""
import json
import random

# ============================================================
# 意图体系完整定义
# ============================================================

INTENT_TAXONOMY = {
    # INFO类 - 信息查询
    "INFO_ACC_BALANCE": "余额查询",
    "INFO_ACC_DETAIL": "账户明细",
    "INFO_ACC_STATUS": "账户状态",
    "INFO_ACC_INFO": "账户信息",
    "INFO_BILL_AMOUNT": "账单金额",
    "INFO_BILL_DATE": "还款日期",
    "INFO_BILL_MIN": "最低还款",
    "INFO_BILL_POINT": "积分查询",
    "INFO_TRAN_RECORD": "交易记录",
    "INFO_TRAN_STATUS": "交易状态",
    "INFO_PROD_WEALTH": "理财信息",
    "INFO_PROD_LOAN": "贷款信息",
    "INFO_PROD_CREDIT": "信用卡信息",
    "INFO_BRANCH": "网点查询",
    "INFO_PHONE": "电话查询",
    "INFO_HOUR": "营业时间",
    "INFO_PROG_APPLICATION": "申请进度",
    "INFO_PROG_TRANSFER": "转账进度",

    # BIZ类 - 业务办理
    "BIZ_TRAN_INTERNAL": "行内转账",
    "BIZ_TRAN_EXTERNAL": "跨行转账",
    "BIZ_TRAN_LIMIT": "转账限额",
    "BIZ_CARD_LOSS": "卡片挂失",
    "BIZ_CARD_ACTIVATE": "卡片激活",
    "BIZ_CARD_REISSUE": "补办新卡",
    "BIZ_CARD_CANCEL": "注销卡片",
    "BIZ_PWD_RESET": "密码重置",
    "BIZ_PWD_CHANGE": "密码修改",
    "BIZ_PAY_REPAY": "主动还款",
    "BIZ_PAY_AUTOPAY": "自动还款",
    "BIZ_INSTALLMENT": "分期办理",

    # CONSULT类 - 咨询投诉
    "CONS_PROD_WEALTH": "理财咨询",
    "CONS_PROD_LOAN": "贷款咨询",
    "CONS_PROD_CREDIT": "信用卡咨询",
    "CONS_FEE_TRAN": "转账手续费",
    "CONS_FEE_WITHDRW": "取现手续费",
    "CONS_FEE_INSTALL": "分期手续费",
    "CONS_COMP_SERVICE": "服务投诉",
    "CONS_COMP_DELAY": "延误投诉",
    "CONS_URG_HUMAN": "转人工",
    "CONS_URG_LOSS": "资金损失",

    # SALES类 - 营销推广
    "SALES_WEALTH_PROD": "理财推荐",
    "SALES_LOAN_PROD": "贷款推荐",
    "SALES_LOAN_RATE": "贷款利率咨询",
    "SALES_CREDIT_PROD": "信用卡推荐",
    "SALES_CREDIT_POINT": "积分活动",

    # SECURITY类 - P0
    "SEC_FRAUD_REPORT": "诈骗举报",
    "SEC_FRAUD_SUSPECT": "可疑交易",
    "SEC_STOLEN_CARD": "卡片盗刷",
    "SEC_STOLEN_INFO": "信息泄露",
    "SEC_FREEZE_UNEXPECTED": "异常冻结",

    # SYSTEM类
    "SYS_GREETING": "问候",
    "SYS_THANKS": "感谢",
    "SYS_BYE": "告别",
    "SYS_INVALID": "无效输入",
}


# ============================================================
# 多意图样本模板（核心意图 + 次要意图）
# ============================================================

MULTI_INTENT_SAMPLES = {
    "INFO_ACC_BALANCE": [
        # 单意图
        {"question": "卡里还有多少钱", "core_intent": "查询余额", "secondary_intent": None},
        {"question": "我的账户余额多少", "core_intent": "查询余额", "secondary_intent": None},
        # 多意图 - 带卡号识别
        {"question": "帮我查下尾号6222那张卡的余额", "core_intent": "查询指定卡余额", "secondary_intent": "识别卡号尾号"},
        {"question": "我的招行卡（卡号后四位1234）还剩多少钱", "core_intent": "查询指定卡余额", "secondary_intent": "卡号对应"},
        # 多意图 - 带金额描述
        {"question": "我那张5000块的卡还有多少余额", "core_intent": "查询余额", "secondary_intent": "金额-卡号映射"},
        # 复杂场景
        {"question": "上个月转了2万进去，现在卡里还剩多少", "core_intent": "查询余额", "secondary_intent": "参考历史交易"},
    ],
    
    "INFO_BILL_AMOUNT": [
        # 单意图
        {"question": "本期账单多少", "core_intent": "查询账单金额", "secondary_intent": None},
        {"question": "我要还多少", "core_intent": "查询账单金额", "secondary_intent": None},
        # 多意图 - 带卡号
        {"question": "帮我查下我的5000块钱，也就是尾号是6222那张卡的账单", "core_intent": "查询账单金额", "secondary_intent": "金额-卡号识别"},
        {"question": "我卡里欠了3万，账单多少", "core_intent": "查询账单金额", "secondary_intent": "金额上下文"},
        # 复杂场景
        {"question": "招商银行的信用卡，上个月消费了15000，现在账单是多少", "core_intent": "查询账单金额", "secondary_intent": "时间范围+金额"},
        {"question": "如果我还了最低还款，下个月账单会变多少", "core_intent": "查询账单预估", "secondary_intent": "计算逻辑"},
    ],
    
    "INFO_BILL_DATE": [
        {"question": "还款日是哪天", "core_intent": "查询还款日", "secondary_intent": None},
        {"question": "我的卡几号要还钱", "core_intent": "查询还款日", "secondary_intent": None},
        {"question": "尾号8899的卡还款截止日期是什么时候", "core_intent": "查询指定卡还款日", "secondary_intent": "识别卡号"},
        {"question": "我已经还了最低还款，但想知道下个还款日是哪天", "core_intent": "查询还款日", "secondary_intent": "上下文延续"},
    ],
    
    "INFO_TRAN_RECORD": [
        {"question": "查一下最近的消费记录", "core_intent": "查询交易记录", "secondary_intent": None},
        {"question": "最近有什么消费", "core_intent": "查询交易记录", "secondary_intent": None},
        {"question": "我上周在超市刷了一笔，能查下明细吗", "core_intent": "查询交易明细", "secondary_intent": "时间+场景"},
        {"question": "招商银行app上那笔300块的消费是什么时候", "core_intent": "查询交易详情", "secondary_intent": "金额定位"},
    ],
    
    "BIZ_CARD_LOSS": [
        {"question": "我的卡丢了", "core_intent": "卡片挂失", "secondary_intent": None},
        {"question": "卡不见了怎么办", "core_intent": "卡片挂失", "secondary_intent": None},
        {"question": "我的招行卡丢失了，帮我挂失一下，卡号后四位是5566", "core_intent": "卡片挂失", "secondary_intent": "提供卡号"},
        {"question": "刚才在商场发现卡不见了，怕被人盗刷，赶紧帮我挂失", "core_intent": "紧急挂失", "secondary_intent": "风险担忧"},
        {"question": "我人在外地，卡丢了能异地挂失吗", "core_intent": "卡片挂失咨询", "secondary_intent": "异地处理"},
    ],
    
    "BIZ_TRAN_EXTERNAL": [
        {"question": "跨行转账怎么操作", "core_intent": "跨行转账", "secondary_intent": None},
        {"question": "转10000到工行卡", "core_intent": "跨行转账", "secondary_intent": "指定金额"},
        {"question": "我要转5万到建设银行，限额多少", "core_intent": "跨行转账咨询", "secondary_intent": "查询限额"},
        {"question": "招商往工商转5万多久到账", "core_intent": "跨行转账", "secondary_intent": "到账时间"},
        {"question": "同行转账和跨行转账手续费一样吗", "core_intent": "跨行转账咨询", "secondary_intent": "费用对比"},
    ],
    
    "BIZ_PAY_REPAY": [
        {"question": "怎么还款", "core_intent": "还款操作", "secondary_intent": None},
        {"question": "信用卡怎么还钱", "core_intent": "还款操作", "secondary_intent": None},
        {"question": "我绑定的是招行卡，能自动扣吗", "core_intent": "还款咨询", "secondary_intent": "自动扣款咨询"},
        {"question": "绑定的还款卡里余额不足，会影响自动还款吗", "core_intent": "还款问题", "secondary_intent": "异常处理"},
    ],
    
    "CONS_PROD_LOAN": [
        {"question": "贷款利息多少", "core_intent": "贷款咨询", "secondary_intent": None},
        {"question": "信用贷款怎么申请", "core_intent": "贷款咨询", "secondary_intent": None},
        {"question": "我有社保和公积金，能贷多少", "core_intent": "贷款额度评估", "secondary_intent": "资质评估"},
        {"question": "贷款10万，分12期还，每月还多少", "core_intent": "贷款还款计算", "secondary_intent": "分期计算"},
        {"question": "信用贷和抵押贷有什么区别", "core_intent": "贷款产品对比", "secondary_intent": "产品比较"},
        {"question": "招行的信用贷利率比网商银行低吗", "core_intent": "贷款利率对比", "secondary_intent": "竞品对比"},
    ],
    
    "CONS_PROD_CREDIT": [
        {"question": "信用卡额度多少", "core_intent": "额度查询", "secondary_intent": None},
        {"question": "我的卡能刷多少", "core_intent": "额度查询", "secondary_intent": None},
        {"question": "临时额度怎么申请，能调多少", "core_intent": "临时额度咨询", "secondary_intent": "额度调整"},
        {"question": "我经常用卡消费，会提额吗", "core_intent": "额度咨询", "secondary_intent": "提额政策"},
        {"question": "固额和临额有什么区别", "core_intent": "额度类型咨询", "secondary_intent": "概念区分"},
    ],
    
    "SEC_FRAUD_REPORT": [
        {"question": "我被骗了", "core_intent": "诈骗举报", "secondary_intent": None},
        {"question": "遇到诈骗怎么办", "core_intent": "诈骗举报", "secondary_intent": None},
        {"question": "刚才接了个电话说是我领导让我转账，转了2万才发现不对", "core_intent": "紧急诈骗举报", "secondary_intent": "时间紧迫+金额"},
        {"question": "收到短信说可以帮我做贷款，但我先交1000手续费，这算诈骗吗", "core_intent": "可疑诈骗咨询", "secondary_intent": "诈骗识别"},
        {"question": "有个自称是银行的人说要给我提额，要我验证密码", "core_intent": "诈骗识别", "secondary_intent": "风险提示"},
    ],
    
    "SEC_STOLEN_CARD": [
        {"question": "卡被人盗刷了", "core_intent": "卡片盗刷", "secondary_intent": None},
        {"question": "收到短信说在境外消费了5000，但我没出国", "core_intent": "可疑交易举报", "secondary_intent": "陌生交易"},
        {"question": "凌晨3点卡被刷了3笔，我能追回来吗", "core_intent": "紧急盗刷处理", "secondary_intent": "时间+金额"},
        {"question": "我的卡在身上但收到消费提醒，卡片复制了吗", "core_intent": "卡片安全咨询", "secondary_intent": "风险评估"},
    ],
    
    "CONS_URG_HUMAN": [
        {"question": "转人工", "core_intent": "转人工服务", "secondary_intent": None},
        {"question": "我要投诉", "core_intent": "投诉处理", "secondary_intent": None},
        {"question": "你们客服太慢了，等了20分钟都没人", "core_intent": "投诉", "secondary_intent": "等待投诉"},
        {"question": "我的卡被盗刷了，必须马上转人工处理", "core_intent": "紧急转人工", "secondary_intent": "P0优先级"},
    ],
    
    "CONS_COMP_SERVICE": [
        {"question": "服务态度太差了", "core_intent": "服务投诉", "secondary_intent": None},
        {"question": "上次有个客服态度很差，帮我反馈一下", "core_intent": "投诉反馈", "secondary_intent": "历史记录"},
        {"question": "你们银行的柜员脸太臭了", "core_intent": "服务投诉", "secondary_intent": "情绪表达"},
    ],
    
    "SALES_WEALTH_PROD": [
        {"question": "有什么好理财产品", "core_intent": "理财推荐", "secondary_intent": None},
        {"question": "想买理财，5万块有什么推荐", "core_intent": "理财推荐", "secondary_intent": "金额+产品"},
        {"question": "稳健型有什么收益高的产品", "core_intent": "理财咨询", "secondary_intent": "风险偏好"},
        {"question": "招行理财和支付宝理财哪个好", "core_intent": "理财产品对比", "secondary_intent": "竞品对比"},
    ],
    
    "SYS_GREETING": [
        {"question": "你好", "core_intent": "问候", "secondary_intent": None},
        {"question": "您好", "core_intent": "问候", "secondary_intent": None},
    ],
}


# ============================================================
# 单意图样本模板（用于扩充）
# ============================================================

SINGLE_INTENT_SAMPLES = {
    "INFO_ACC_BALANCE": [
        "余额查询",
        "我的账户还有多少",
        "查一下卡上剩多少钱",
        "账户余额多少",
        "招行卡还有钱吗",
    ],
    "INFO_ACC_DETAIL": [
        "查一下交易明细",
        "最近消费明细",
        "历史交易记录",
        "账单明细",
        "消费流水",
    ],
    "INFO_BILL_AMOUNT": [
        "本期账单",
        "信用卡欠款",
        "账单金额",
        "这个月要还多少",
        "欠银行多少钱",
    ],
    "INFO_BILL_DATE": [
        "还款截止日",
        "最晚什么时候还款",
        "几号之前要还",
        "还款日期",
        "哪天是还款日",
    ],
    "INFO_BILL_MIN": [
        "最低还款多少",
        "最少还多少钱",
        "最低还款额",
    ],
    "INFO_BILL_POINT": [
        "积分有多少",
        "积分怎么用",
        "我的积分",
        "查积分",
    ],
    "INFO_BRANCH": [
        "附近网点在哪",
        "最近的支行",
        "招行网点地址",
    ],
    "INFO_HOUR": [
        "营业时间",
        "几点开门",
        "网点几点下班",
    ],
    "INFO_PROG_TRANSFER": [
        "转账多久到账",
        "到账时间",
        "跨行转账要多久",
    ],
    "BIZ_CARD_ACTIVATE": [
        "怎么激活卡片",
        "开卡",
        "新卡激活",
    ],
    "BIZ_CARD_REISSUE": [
        "补办新卡",
        "卡坏了要换",
        "补卡",
    ],
    "BIZ_CARD_CANCEL": [
        "注销卡片",
        "销卡",
    ],
    "BIZ_PWD_RESET": [
        "忘记密码",
        "密码忘了",
        "重置密码",
    ],
    "BIZ_PWD_CHANGE": [
        "改密码",
        "换密码",
        "修改密码",
    ],
    "BIZ_INSTALLMENT": [
        "分期付款",
        "账单分期",
        "消费分期",
    ],
    "CONS_PROD_WEALTH": [
        "理财怎么样",
        "理财产品收益",
        "想了解理财",
    ],
    "CONS_FEE_TRAN": [
        "转账手续费多少",
        "跨行费用",
        "手续费",
    ],
    "CONS_FEE_WITHDRW": [
        "取现手续费",
        "提现费用",
    ],
    "CONS_URG_LOSS": [
        "钱被骗了",
        "资金损失",
        "我被诈骗了",
    ],
    "SALES_LOAN_PROD": [
        "贷款推荐",
        "有什么贷款",
        "推荐贷款产品",
    ],
    "SALES_LOAN_RATE": [
        "贷款利率多少",
        "贷款利息",
    ],
    "SALES_CREDIT_PROD": [
        "推荐信用卡",
        "办什么卡好",
    ],
    "SALES_CREDIT_POINT": [
        "积分兑换",
        "打折活动",
        "优惠活动",
    ],
    "SEC_FRAUD_SUSPECT": [
        "可疑交易",
        "陌生消费",
        "账户异常",
    ],
    "SEC_STOLEN_INFO": [
        "信息泄露",
        "资料被盗",
    ],
    "SEC_FREEZE_UNEXPECTED": [
        "卡被冻结了",
        "账户冻结",
        "卡不能用",
    ],
    "SYS_THANKS": [
        "谢谢",
        "感谢",
    ],
    "SYS_BYE": [
        "再见",
        "拜拜",
    ],
    "SYS_INVALID": [
        "嗯",
        "啊",
        "呃",
        "听不懂",
    ],
}


# ============================================================
# 样本生成
# ============================================================

def generate_samples(target_count=1000):
    """生成指定数量的样本"""
    samples = []
    sample_id = 1

    # 计算每种意图需要多少样本
    intent_counts = {
        # INFO类 - 高频
        "INFO_BILL_AMOUNT": 100,
        "INFO_ACC_BALANCE": 60,
        "INFO_BILL_DATE": 50,
        "INFO_TRAN_RECORD": 40,
        "INFO_BRANCH": 30,
        "INFO_HOUR": 20,
        "INFO_BILL_MIN": 20,
        "INFO_BILL_POINT": 15,
        "INFO_PROD_CREDIT": 20,
        "INFO_PROD_LOAN": 15,
        "INFO_PROD_WEALTH": 15,

        # BIZ类 - 高频
        "BIZ_CARD_LOSS": 80,
        "BIZ_TRAN_EXTERNAL": 60,
        "BIZ_PAY_REPAY": 50,
        "BIZ_PWD_RESET": 30,
        "BIZ_CARD_ACTIVATE": 25,
        "BIZ_CARD_REISSUE": 20,
        "BIZ_TRAN_INTERNAL": 30,
        "BIZ_INSTALLMENT": 20,

        # CONSULT类 - 重要
        "CONS_PROD_LOAN": 60,
        "CONS_PROD_CREDIT": 50,
        "CONS_PROD_WEALTH": 30,
        "CONS_URG_HUMAN": 50,
        "CONS_COMP_SERVICE": 25,
        "CONS_COMP_DELAY": 15,
        "CONS_URG_LOSS": 20,

        # SECURITY类 - P0
        "SEC_FRAUD_REPORT": 40,
        "SEC_STOLEN_CARD": 30,
        "SEC_FRAUD_SUSPECT": 20,
        "SEC_FREEZE_UNEXPECTED": 15,

        # SALES类 - 次要
        "SALES_WEALTH_PROD": 25,
        "SALES_LOAN_PROD": 20,
        "SALES_LOAN_RATE": 15,
        "SALES_CREDIT_PROD": 15,
        "SALES_CREDIT_POINT": 15,

        # SYS类 - 兜底
        "SYS_GREETING": 30,
        "SYS_THANKS": 20,
        "SYS_BYE": 15,
        "SYS_INVALID": 15,
    }

    for intent, target_count_intent in intent_counts.items():
        templates = MULTI_INTENT_SAMPLES.get(intent, [])
        single_templates = SINGLE_INTENT_SAMPLES.get(intent, [])

        # 计算多意图样本比例（40%）
        multi_count = int(target_count_intent * 0.4)
        single_count = target_count_intent - multi_count

        # 生成多意图样本
        for i in range(multi_count):
            template = templates[i % len(templates)] if templates else {}
            question = template.get("question", f"查询{intent}")
            core_intent = template.get("core_intent", "")
            secondary_intent = template.get("secondary_intent")

            sample = {
                "id": f"SMART_{sample_id:05d}",
                "intent": intent.lower(),
                "question": question,
                "core_intent": core_intent,
                "secondary_intent": secondary_intent,
                "has_secondary": secondary_intent is not None,
                "is_p0": intent.startswith("SEC_") or intent in ["CONS_URG_HUMAN", "CONS_URG_LOSS"],
            }
            samples.append(sample)
            sample_id += 1

        # 生成单意图样本（减少，为多意图腾出空间）
        for i in range(single_count):
            question = single_templates[i % len(single_templates)] if single_templates else f"查询{intent.lower()}"
            sample = {
                "id": f"SMART_{sample_id:05d}",
                "intent": intent.lower(),
                "question": question,
                "core_intent": INTENT_TAXONOMY.get(intent.upper(), intent),
                "secondary_intent": None,
                "has_secondary": False,
                "is_p0": intent.startswith("SEC_") or intent in ["CONS_URG_HUMAN", "CONS_URG_LOSS"],
            }
            samples.append(sample)
            sample_id += 1

    # 打乱顺序
    random.shuffle(samples)

    # 如果数量不够，补充
    while len(samples) < target_count:
        intent = random.choice(list(intent_counts.keys()))
        templates = SINGLE_INTENT_SAMPLES.get(intent, ["查询"])
        sample = {
            "id": f"SMART_{sample_id:05d}",
            "intent": intent.lower(),
            "question": random.choice(templates),
            "core_intent": INTENT_TAXONOMY.get(intent.upper(), intent),
            "secondary_intent": None,
            "has_secondary": False,
            "is_p0": intent.startswith("SEC_"),
        }
        samples.append(sample)
        sample_id += 1

    return samples[:target_count]


def main():
    print("生成评测数据集 v5.0 (真实复杂场景)...")
    samples = generate_samples(target_count=1000)

    print(f"生成了 {len(samples)} 条样本")

    # 统计
    multi_count = sum(1 for s in samples if s.get("has_secondary"))
    print(f"  - 多意图样本: {multi_count} ({multi_count/len(samples)*100:.1f}%)")
    print(f"  - 单意图样本: {len(samples) - multi_count}")

    # 意图分布
    intent_counts = {}
    for s in samples:
        intent = s["intent"]
        intent_counts[intent] = intent_counts.get(intent, 0) + 1

    print(f"\n覆盖 {len(intent_counts)} 种意图")

    # 类别分布
    category_counts = {}
    for s in samples:
        cat = s["intent"].split("_")[0].upper()
        category_counts[cat] = category_counts.get(cat, 0) + 1

    print("\n类别分布:")
    for cat, count in sorted(category_counts.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")

    # 保存
    dataset = {
        "dataset_version": "v5.0",
        "total_samples": len(samples),
        "generated_date": "2026-06-01",
        "description": "招行智能客服评测数据集v5.0 - 真实复杂场景 + 多意图",
        "multi_intent_count": multi_count,
        "intent_count": len(intent_counts),
        "samples": samples
    }

    output_path = "data/evaluation_dataset_v5.0.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    print(f"\n已保存到 {output_path}")


if __name__ == "__main__":
    main()