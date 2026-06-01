"""
评测数据集生成器 v5.1
修复v5.0的占位符问题，使用真实用户问题
"""
import json
import random

# 真实用户问题模板（每种意图多条）
REAL_SAMPLES = {
    "info_acc_balance": [
        "卡里还有多少钱",
        "账户余额多少",
        "我的招行卡还有钱吗",
        "余额查询",
        "还剩多少",
    ],
    "info_acc_detail": [
        "查一下交易明细",
        "消费记录怎么查",
        "最近有什么消费",
        "账单明细",
        "交易流水",
    ],
    "info_bill_amount": [
        "本期账单多少",
        "我欠了多少钱",
        "账单金额是多少",
        "要还多少",
        "信用卡欠款",
    ],
    "info_bill_date": [
        "还款日是哪天",
        "几号要还钱",
        "截止日期",
        "最晚什么时候还款",
    ],
    "info_tran_record": [
        "查交易记录",
        "消费明细",
        "最近消费",
        "交易流水",
    ],
    "info_branch": [
        "附近网点在哪",
        "最近的支行地址",
        "招行网点查询",
    ],
    "info_hour": [
        "几点开门",
        "营业时间",
        "网点几点下班",
    ],
    "biz_card_loss": [
        "我的卡丢了",
        "卡不见了怎么办",
        "要挂失",
        "卡丢了",
    ],
    "biz_card_activate": [
        "怎么激活卡片",
        "新卡怎么开",
        "卡片激活",
    ],
    "biz_tran_external": [
        "跨行转账怎么转",
        "转10000到工行",
        "转账到别的银行",
    ],
    "biz_tran_internal": [
        "行内转账",
        "转钱到招行卡",
    ],
    "biz_pay_repay": [
        "怎么还款",
        "还信用卡",
        "主动还款",
    ],
    "biz_pwd_reset": [
        "忘记密码",
        "密码忘了怎么办",
        "重置密码",
    ],
    "cons_prod_loan": [
        "贷款利息多少",
        "信用贷怎么申请",
        "贷款额度多少",
    ],
    "cons_prod_credit": [
        "信用卡额度多少",
        "年费多少",
        "申请信用卡",
    ],
    "cons_prod_wealth": [
        "理财产品怎么样",
        "理财收益多少",
        "有什么好理财",
    ],
    "cons_fee_tran": [
        "转账手续费多少",
        "跨行费用",
    ],
    "cons_urg_human": [
        "转人工",
        "找客服",
        "需要人工服务",
    ],
    "cons_urg_loss": [
        "钱被骗了",
        "被诈骗了",
        "资金损失",
    ],
    "cons_comp_service": [
        "服务态度差",
        "投诉",
        "态度不好",
    ],
    "sec_fraud_report": [
        "我被骗了",
        "遇到诈骗",
        "举报诈骗",
    ],
    "sec_stolen_card": [
        "卡被盗刷了",
        "收到陌生消费",
        "卡片异常",
    ],
    "sec_freeze_unexpected": [
        "卡被冻结了",
        "账户异常冻结",
        "卡不能用了",
    ],
    "sales_wealth_prod": [
        "推荐理财产品",
        "有什么好理财",
    ],
    "sales_loan_prod": [
        "贷款推荐",
        "有什么贷款产品",
    ],
    "sales_loan_rate": [
        "贷款利率多少",
        "贷款利息咨询",
    ],
    "sales_credit_prod": [
        "推荐信用卡",
        "办什么卡好",
    ],
    "sys_greeting": [
        "你好",
        "您好",
        "在吗",
    ],
    "sys_thanks": [
        "谢谢",
        "感谢",
        "好的谢谢",
    ],
    "sys_bye": [
        "再见",
        "拜拜",
        "我先走了",
    ],
    "sys_invalid": [
        "嗯",
        "啊",
        "呃",
        "听不懂",
    ],
}

def generate_dataset(target_count=1000):
    samples = []
    sample_id = 1

    # 意图权重
    intent_weights = {
        "info_bill_amount": 100,
        "info_acc_balance": 60,
        "biz_card_loss": 80,
        "biz_tran_external": 50,
        "cons_urg_human": 50,
        "cons_prod_loan": 40,
        "cons_prod_credit": 40,
        "sec_fraud_report": 40,
        "sec_stolen_card": 30,
        "cons_prod_wealth": 30,
        "biz_pay_repay": 40,
        "cons_comp_service": 25,
        "info_tran_record": 30,
        "info_branch": 25,
        "info_hour": 20,
        "cons_urg_loss": 20,
        "info_bill_date": 40,
        "biz_pwd_reset": 30,
        "biz_card_activate": 25,
        "sales_wealth_prod": 25,
        "sales_loan_prod": 20,
        "sales_credit_prod": 15,
        "sys_greeting": 40,
        "sys_thanks": 20,
        "sys_bye": 20,
        "sys_invalid": 15,
        "cons_fee_tran": 20,
        "sec_freeze_unexpected": 20,
        "info_acc_detail": 20,
        "biz_tran_internal": 30,
        "sales_loan_rate": 15,
    }

    for intent, count in intent_weights.items():
        templates = REAL_SAMPLES.get(intent, [])
        if not templates:
            continue

        for i in range(count):
            question = templates[i % len(templates)]
            sample = {
                "id": f"SMART_{sample_id:05d}",
                "intent": intent,
                "question": question,
                "is_p0": intent.startswith("sec_") or intent in ["cons_urg_human", "cons_urg_loss"],
            }
            samples.append(sample)
            sample_id += 1

    # 打乱
    random.shuffle(samples)
    return samples[:target_count]

if __name__ == "__main__":
    samples = generate_dataset(600)

    print(f"生成了 {len(samples)} 条样本")

    # 统计
    intent_counts = {}
    for s in samples:
        intent_counts[s['intent']] = intent_counts.get(s['intent'], 0) + 1

    print(f"覆盖 {len(intent_counts)} 种意图")
    print()
    print("意图分布:")
    for intent, count in sorted(intent_counts.items(), key=lambda x: -x[1])[:15]:
        print(f"  {intent:25s}: {count}")

    # 保存
    dataset = {
        "dataset_version": "v5.1",
        "total_samples": len(samples),
        "generated_date": "2026-06-01",
        "description": "修复版数据集 - 真实用户问题",
        "samples": samples
    }

    with open("data/evaluation_dataset_v5.1.json", "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    print("\n已保存到 data/evaluation_dataset_v5.1.json")