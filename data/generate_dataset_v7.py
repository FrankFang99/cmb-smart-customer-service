"""
v3.5.4 扩评测集 1500 -> 3000 样本 (种子问题 + 模板扩展)
======================================================

策略 (用户反馈): 不再靠同义词改写, 用**种子问题 + 模板扩展**
- 写 50+ 真实种子问题 (覆盖每意图 + 每 P0 子类)
- 用 12 种模板生成 3000 样本
- 保留 train/holdout 拆分 (种子 42)
- 重点: P0 样本从 214 -> 400+ (扩 2x, 关键安全指标)

为什么种子问题优先改写:
- 改写只是同义变换, 新意图覆盖不到
- 种子问题能覆盖真实业务场景
- 招行业务团队手工整理的种子最稳
"""

from __future__ import annotations

import json
import random
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

_ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = _ROOT / "data" / "evaluation_dataset_v6.0.json"
OUTPUT_PATH = _ROOT / "data" / "evaluation_dataset_v7.0.json"


# ============================================================
# 50+ 人工种子问题 (覆盖关键业务, 重点 P0)
# ============================================================
SEED_SAMPLES = [
    # ===== P0 紧急转人工 (重点扩充) =====
    {"intent": "cons_urg_human", "is_p0": True, "q": "我要投诉, 转人工"},
    {"intent": "cons_urg_human", "is_p0": True, "q": "马上转人工, 别废话"},
    {"intent": "cons_urg_human", "is_p0": True, "q": "我要和真人说话"},
    {"intent": "cons_urg_human", "is_p0": True, "q": "机器人解决不了, 转人"},
    {"intent": "cons_urg_human", "is_p0": True, "q": "需要 95555 人工"},
    {"intent": "cons_urg_human", "is_p0": True, "q": "帮我接人工"},
    {"intent": "cons_urg_human", "is_p0": True, "q": "可以转人工吗"},
    # P0 反诈
    {"intent": "sec_fraud_report", "is_p0": True, "q": "我被诈骗了 5 万"},
    {"intent": "sec_fraud_report", "is_p0": True, "q": "刚被骗了 10 万, 怎么办"},
    {"intent": "sec_fraud_report", "is_p0": True, "q": "信用卡被盗刷了"},
    {"intent": "sec_fraud_report", "is_p0": True, "q": "陌生人让我转账到安全账户"},
    {"intent": "sec_fraud_report", "is_p0": True, "q": "我好像碰到电信诈骗了"},
    {"intent": "sec_fraud_report", "is_p0": True, "q": "有人冒充招行客服要验证码"},
    # P0 账户异常
    {"intent": "sec_freeze_unexpected", "is_p0": True, "q": "我的账户怎么被冻了"},
    {"intent": "sec_freeze_unexpected", "is_p0": True, "q": "卡突然不能用了, 是不是被冻"},
    {"intent": "sec_freeze_unexpected", "is_p0": True, "q": "账户异常, 怎么解冻"},
    {"intent": "sec_freeze_unexpected", "is_p0": True, "q": "卡被锁住了"},
    {"intent": "sec_freeze_unexpected", "is_p0": True, "q": "账户状态异常"},
    # P0 盗刷
    {"intent": "sec_stolen_card", "is_p0": True, "q": "卡上有一笔陌生消费"},
    {"intent": "sec_stolen_card", "is_p0": True, "q": "收到陌生消费提醒"},
    {"intent": "sec_stolen_card", "is_p0": True, "q": "我没消费但卡被刷了"},
    {"intent": "sec_stolen_card", "is_p0": True, "q": "卡被刷 1000 元不是我"},
    {"intent": "sec_stolen_card", "is_p0": True, "q": "信用卡有笔消费不是我的"},
    # P0 紧急损失
    {"intent": "cons_urg_loss", "is_p0": True, "q": "刚被骗了怎么办"},
    {"intent": "cons_urg_loss", "is_p0": True, "q": "卡丢了被刷了"},
    {"intent": "cons_urg_loss", "is_p0": True, "q": "损失了 5 万, 紧急"},
    # ===== sys (高覆盖) =====
    {"intent": "sys_greeting", "is_p0": False, "q": "你好"},
    {"intent": "sys_greeting", "is_p0": False, "q": "您好, 我有问题咨询"},
    {"intent": "sys_greeting", "is_p0": False, "q": "在吗"},
    {"intent": "sys_bye", "is_p0": False, "q": "再见"},
    {"intent": "sys_bye", "is_p0": False, "q": "谢谢, 拜拜"},
    {"intent": "sys_thanks", "is_p0": False, "q": "谢谢"},
    {"intent": "sys_thanks", "is_p0": False, "q": "非常感谢"},
    {"intent": "sys_invalid", "is_p0": False, "q": "asdfgh"},
    {"intent": "sys_invalid", "is_p0": False, "q": "???"},
    # ===== info 查询 =====
    {"intent": "info_acc_balance", "is_p0": False, "q": "我卡里还有多少钱"},
    {"intent": "info_acc_balance", "is_p0": False, "q": "查询账户余额"},
    {"intent": "info_acc_balance", "is_p0": False, "q": "余额多少"},
    {"intent": "info_bill_amount", "is_p0": False, "q": "我的信用卡账单多少"},
    {"intent": "info_bill_amount", "is_p0": False, "q": "这期账单金额"},
    {"intent": "info_bill_date", "is_p0": False, "q": "什么时候还款"},
    {"intent": "info_bill_date", "is_p0": False, "q": "最晚还款日"},
    {"intent": "info_bill_point", "is_p0": False, "q": "我有多少积分"},
    {"intent": "info_bill_point", "is_p0": False, "q": "积分怎么查"},
    {"intent": "info_tran_record", "is_p0": False, "q": "查一下交易明细"},
    {"intent": "info_tran_record", "is_p0": False, "q": "最近的交易记录"},
    {"intent": "info_branch", "is_p0": False, "q": "招行网点在哪"},
    {"intent": "info_branch", "is_p0": False, "q": "附近的招行"},
    {"intent": "info_phone", "is_p0": False, "q": "招行电话多少"},
    {"intent": "info_phone", "is_p0": False, "q": "95555 怎么打"},
    # ===== biz 业务办理 =====
    {"intent": "biz_card_activate", "is_p0": False, "q": "怎么激活信用卡"},
    {"intent": "biz_card_activate", "is_p0": False, "q": "新卡怎么开卡"},
    {"intent": "biz_card_loss", "is_p0": False, "q": "信用卡丢了怎么办"},
    {"intent": "biz_card_loss", "is_p0": False, "q": "挂失信用卡"},
    {"intent": "biz_card_reissue", "is_p0": False, "q": "补办新卡"},
    {"intent": "biz_pwd_reset", "is_p0": False, "q": "密码忘了, 怎么重置"},
    {"intent": "biz_pwd_change", "is_p0": False, "q": "怎么改密码"},
    {"intent": "biz_tran_limit", "is_p0": False, "q": "转账限额多少"},
    {"intent": "biz_tran_limit", "is_p0": False, "q": "单笔能转多少"},
    {"intent": "biz_pay_repay", "is_p0": False, "q": "怎么还款"},
    {"intent": "biz_pay_repay", "is_p0": False, "q": "主动还款怎么操作"},
    {"intent": "biz_installment", "is_p0": False, "q": "怎么分期"},
    {"intent": "biz_installment", "is_p0": False, "q": "账单分期手续费"},
    # ===== sales 营销 =====
    {"intent": "sales_wealth_prod", "is_p0": False, "q": "有什么好理财"},
    {"intent": "sales_wealth_prod", "is_p0": False, "q": "理财推荐"},
    {"intent": "sales_wealth_prod", "is_p0": False, "q": "朝朝宝怎么样"},
    {"intent": "sales_credit_prod", "is_p0": False, "q": "办什么信用卡好"},
    {"intent": "sales_credit_prod", "is_p0": False, "q": "推荐一张信用卡"},
    {"intent": "sales_loan_prod", "is_p0": False, "q": "招行信用贷"},
    # ===== cons 咨询 =====
    {"intent": "cons_prod_credit", "is_p0": False, "q": "申请信用卡"},
    {"intent": "cons_prod_loan", "is_p0": False, "q": "贷款怎么办"},
    {"intent": "cons_prod_wealth", "is_p0": False, "q": "理财产品推荐"},
    {"intent": "cons_comp_service", "is_p0": False, "q": "我要投诉"},
    {"intent": "cons_comp_service", "is_p0": False, "q": "客服态度差"},
]


# 12 种模板 (基于种子的句式变换)
TEMPLATES = [
    lambda q: q,  # 原句
    lambda q: "请问" + q,  # 加请问
    lambda q: q + "?",  # 加问号
    lambda q: "想问一下" + q,  # 加想问一下
    lambda q: q + "谢谢",  # 加谢谢
    lambda q: q.replace("?", "？").replace("吗", "吗？"),  # 加中文问号
    lambda q: "那个" + q,  # 加那个
    lambda q: q + "怎么弄",  # 加怎么弄
    lambda q: q + " 怎么处理",  # 加怎么处理
    lambda q: q.replace("我", "我的"),  # 我 -> 我的
    lambda q: "你好, " + q,  # 加你好
    lambda q: "那个" + q + "谢谢",  # 加那个+谢谢
]


def expand_seeds(seeds: List[Dict], target_p0_count: int = 100, target_per_intent: int = 60, seed: int = 42) -> List[Dict]:
    """
    扩展种子问题到目标样本数
    - P0 意图: target_p0_count (重点, 招行实战 ~14% P0 比例, 8 意图 × 100 = 800 + 12 意图 × 60 = 720 = 1520)
    - 其他意图: target_per_intent
    """
    random.seed(seed)
    # 按意图分组
    by_intent: Dict[str, List[Dict]] = {}
    for s in seeds:
        by_intent.setdefault(s["intent"], []).append(s)
    expanded = []
    next_id = 7000  # 区别于 v6.0 (V6_xxxx)
    for intent, items in by_intent.items():
        # P0 扩充到 target_p0_count
        is_p0 = items[0].get("is_p0", False)
        target = target_p0_count if is_p0 else target_per_intent
        while len([e for e in expanded if e["intent"] == intent]) < target:
            base = random.choice(items)
            template = random.choice(TEMPLATES)
            new_q = template(base["q"])
            expanded.append({
                "id": f"V7_{next_id:04d}",
                "intent": intent,
                "question": new_q,
                "is_p0": is_p0,
                "source": "seed_v7.0",
            })
            next_id += 1
    return expanded


def split_train_holdout(samples: List[Dict], train_ratio: float = 0.67, seed: int = 42) -> List[Dict]:
    """train/holdout 拆分 (按意图分层抽样)"""
    random.seed(seed)
    by_intent: Dict[str, List[Dict]] = {}
    for s in samples:
        by_intent.setdefault(s.get("intent", "unknown"), []).append(s)
    for intent in by_intent:
        random.shuffle(by_intent[intent])
    train, holdout = [], []
    for intent, items in by_intent.items():
        split = int(len(items) * train_ratio)
        train.extend(items[:split])
        holdout.extend(items[split:])
    for s in train:
        s["split"] = "train"
    for s in holdout:
        s["split"] = "holdout"
    combined = train + holdout
    random.shuffle(combined)
    return combined


def main():
    print("=" * 60)
    print("v3.5.4 扩评测集 1500 -> 3000 种子问题 + train/holdout 拆分")
    print("=" * 60)
    # 加载 v6.0
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        v6 = json.load(f)
    base_samples = v6["samples"]
    print(f"v6.0 基础: {len(base_samples)} 样本")
    # 计算每意图的目标数
    base_intent_count = Counter(s["intent"] for s in base_samples)
    target_per_intent = 3000 // len(base_intent_count) + 50  # 让总样本超 3000
    # 扩种子
    seed_expanded = expand_seeds(
        SEED_SAMPLES,
        target_p0_count=100,  # P0 重点扩 (8 意图 × 100 = 800)
        target_per_intent=60,  # 其他 (12 意图 × 60 = 720)
        seed=42,
    )
    print(f"种子扩展: {len(seed_expanded)} 样本")
    # 合并 (v6.0 全部 + 种子扩展)
    # 给 v6.0 加 split 字段 (如果还没)
    for s in base_samples:
        if "split" not in s:
            s["split"] = "v6_orig"
    combined = list(base_samples) + seed_expanded
    print(f"合并: {len(combined)} 样本")
    # train/holdout 拆分 (基于 v6.0 + 种子扩展)
    split = split_train_holdout(combined, train_ratio=0.67, seed=42)
    train_n = sum(1 for s in split if s.get("split") == "train")
    holdout_n = sum(1 for s in split if s.get("split") == "holdout")
    print(f"train: {train_n}, holdout: {holdout_n}")
    # 分布
    p0_count = sum(1 for s in split if s.get("is_p0", False))
    print(f"P0: {p0_count} ({p0_count/len(split)*100:.1f}%)")
    grp_count = Counter(s.get("intent", "unknown").split("_")[0] for s in split)
    print(f"业务组: {dict(grp_count)}")
    # 输出
    output = {
        "dataset_version": "v7.0",
        "total_samples": len(split),
        "generated_date": "2026-06-12",
        "description": "v6.0 (1500) + 种子问题扩展 (50 种子 + 12 模板) = 3000 样本 - P0 重点扩充到 400+",
        "base_dataset": "evaluation_dataset_v6.0.json",
        "expansion_method": "种子问题 + 句式模板 (非改写)",
        "seed_count": len(SEED_SAMPLES),
        "p0_seed_count": sum(1 for s in SEED_SAMPLES if s.get("is_p0")),
        "train_count": train_n,
        "holdout_count": holdout_n,
        "p0_count": p0_count,
        "samples": split,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n输出: {OUTPUT_PATH}")
    print(f"\n前 5 条样本:")
    for s in split[:5]:
        print("  [%s] %s | intent=%s | Q: %s" % (
            s.get("split", "?"), s["id"], s["intent"], s["question"]))


if __name__ == "__main__":
    main()
