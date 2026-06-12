"""
v3.5.5 种子问题库 (300+ 人工种子 - 对标国有大行标准)
========================================================

设计 (基于 B 站视频 + 招行 App + 工行/中行/建行 实操):
- 12 大业务类 (覆盖 P0 重点 + 高频业务)
- 每业务类 20+ 真实 query (银行 App 帮助中心 + 客服话术 + 客户调研)
- P0 类 50+ (重点: 转人工 / 反诈 / 反洗钱 / 账户异常 / 盗刷 / 紧急损失)
- L0 词典扩到 30 词 (含口语化 P0)

国有大行标准 (工行 / 中行 / 建行 / 农行 / 邮储):
- 智能客服覆盖 90%+ 高频业务
- P0 100% 触发人工 (1 都不能错)
- 口语化 query 覆盖 50+ 变体
"""

from __future__ import annotations

from typing import Dict, List

# ============================================================
# 300+ 人工种子 (对标国有大行真实业务场景)
# ============================================================
SEEDS_V355: Dict[str, List[Dict]] = {
    # ===== P0 第 1 类: cons_urg_human (转人工) - 30 条 =====
    "cons_urg_human": [
        {"q": "我要投诉, 转人工", "is_p0": True, "p0_sub": "urg_human"},
        {"q": "马上转人工, 别废话", "is_p0": True, "p0_sub": "urg_human"},
        {"q": "我要和真人说话", "is_p0": True, "p0_sub": "urg_human"},
        {"q": "机器人解决不了, 转人", "is_p0": True, "p0_sub": "urg_human"},
        {"q": "需要 95555 人工", "is_p0": True, "p0_sub": "urg_human"},
        {"q": "帮我接人工", "is_p0": True, "p0_sub": "urg_human"},
        {"q": "可以转人工吗", "is_p0": True, "p0_sub": "urg_human"},
        {"q": "转人工客服", "is_p0": True, "p0_sub": "urg_human"},
        {"q": "我要找人工", "is_p0": True, "p0_sub": "urg_human"},
        {"q": "找真人客服", "is_p0": True, "p0_sub": "urg_human"},
        {"q": "请帮我转人工", "is_p0": True, "p0_sub": "urg_human"},
        {"q": "转人工谢谢", "is_p0": True, "p0_sub": "urg_human"},
        {"q": "麻烦转人工", "is_p0": True, "p0_sub": "urg_human"},
        {"q": "要 95555 人工服务", "is_p0": True, "p0_sub": "urg_human"},
        {"q": "请转人工坐席", "is_p0": True, "p0_sub": "urg_human"},
        {"q": "我需要人工帮助", "is_p0": True, "p0_sub": "urg_human"},
        {"q": "帮我转接人工", "is_p0": True, "p0_sub": "urg_human"},
        {"q": "人工坐席", "is_p0": True, "p0_sub": "urg_human"},
        {"q": "请接人工", "is_p0": True, "p0_sub": "urg_human"},
        {"q": "真人, 谢谢", "is_p0": True, "p0_sub": "urg_human"},
        {"q": "我要投诉你们的服务", "is_p0": True, "p0_sub": "urg_human"},
        {"q": "服务态度太差了, 转人工", "is_p0": True, "p0_sub": "urg_human"},
        {"q": "客服解决不了, 转人", "is_p0": True, "p0_sub": "urg_human"},
        {"q": "我不跟机器人聊", "is_p0": True, "p0_sub": "urg_human"},
        {"q": "我要和客服说话", "is_p0": True, "p0_sub": "urg_human"},
        {"q": "招行 95555 人工", "is_p0": True, "p0_sub": "urg_human"},
        {"q": "转人工, 投诉", "is_p0": True, "p0_sub": "urg_human"},
        {"q": "人工服务在哪里", "is_p0": True, "p0_sub": "urg_human"},
        {"q": "我需要人工客服", "is_p0": True, "p0_sub": "urg_human"},
        {"q": "在线客服转人工", "is_p0": True, "p0_sub": "urg_human"},
    ],
    # ===== P0 第 2 类: sec_fraud_report (反诈) - 25 条 =====
    "sec_fraud_report": [
        {"q": "我被诈骗了 5 万", "is_p0": True, "p0_sub": "fraud"},
        {"q": "刚被骗了 10 万, 怎么办", "is_p0": True, "p0_sub": "fraud"},
        {"q": "信用卡被盗刷了", "is_p0": True, "p0_sub": "fraud"},
        {"q": "陌生人让我转账到安全账户", "is_p0": True, "p0_sub": "fraud"},
        {"q": "我好像碰到电信诈骗了", "is_p0": True, "p0_sub": "fraud"},
        {"q": "有人冒充招行客服要验证码", "is_p0": True, "p0_sub": "fraud"},
        {"q": "我点了个链接, 卡被盗了", "is_p0": True, "p0_sub": "fraud"},
        {"q": "怀疑被钓鱼网站骗了", "is_p0": True, "p0_sub": "fraud"},
        {"q": "卡里的钱被转走了", "is_p0": True, "p0_sub": "fraud"},
        {"q": "骗子让我转了 8 万", "is_p0": True, "p0_sub": "fraud"},
        {"q": "被骗了怎么办", "is_p0": True, "p0_sub": "fraud"},
        {"q": "我可能遇到诈骗了", "is_p0": True, "p0_sub": "fraud"},
        {"q": "信用卡信息泄露了", "is_p0": True, "p0_sub": "fraud"},
        {"q": "有人假冒公安要钱", "is_p0": True, "p0_sub": "fraud"},
        {"q": "被冒充公检法骗了", "is_p0": True, "p0_sub": "fraud"},
        {"q": "刚接了个诈骗电话", "is_p0": True, "p0_sub": "fraud"},
        {"q": "短信说我中奖了, 是骗子吗", "is_p0": True, "p0_sub": "fraud"},
        {"q": "卡被陌生人盗用", "is_p0": True, "p0_sub": "fraud"},
        {"q": "我好像被网络诈骗了", "is_p0": True, "p0_sub": "fraud"},
        {"q": "账户里钱不见了", "is_p0": True, "p0_sub": "fraud"},
        {"q": "刚给骗子转了钱", "is_p0": True, "p0_sub": "fraud"},
        {"q": "卡里的钱被刷走了", "is_p0": True, "p0_sub": "fraud"},
        {"q": "我被骗了几万块", "is_p0": True, "p0_sub": "fraud"},
        {"q": "刚接了一个诈骗电话", "is_p0": True, "p0_sub": "fraud"},
        {"q": "骗我输入了验证码", "is_p0": True, "p0_sub": "fraud"},
    ],
    # ===== P0 第 3 类: sec_freeze_unexpected (账户异常) - 30 条 (重点扩) =====
    "sec_freeze_unexpected": [
        {"q": "账户异常冻结", "is_p0": True, "p0_sub": "freeze"},
        {"q": "账户异常", "is_p0": True, "p0_sub": "freeze"},
        {"q": "卡被冻了", "is_p0": True, "p0_sub": "freeze"},
        {"q": "卡冻结了", "is_p0": True, "p0_sub": "freeze"},
        {"q": "我的账户怎么被冻了", "is_p0": True, "p0_sub": "freeze"},
        {"q": "卡突然不能用了, 是不是被冻", "is_p0": True, "p0_sub": "freeze"},
        {"q": "账户异常, 怎么解冻", "is_p0": True, "p0_sub": "freeze"},
        {"q": "卡被锁住了", "is_p0": True, "p0_sub": "freeze"},
        {"q": "账户状态异常", "is_p0": True, "p0_sub": "freeze"},
        {"q": "账户被冻结了, 怎么办", "is_p0": True, "p0_sub": "freeze"},
        {"q": "怎么账户被冻了", "is_p0": True, "p0_sub": "freeze"},
        {"q": "我的卡怎么锁住了", "is_p0": True, "p0_sub": "freeze"},
        {"q": "为啥账户被冻", "is_p0": True, "p0_sub": "freeze"},
        {"q": "卡不能用了, 是不是被冻", "is_p0": True, "p0_sub": "freeze"},
        {"q": "账户冻结, 怎么解", "is_p0": True, "p0_sub": "freeze"},
        {"q": "为什么我的卡被冻了", "is_p0": True, "p0_sub": "freeze"},
        {"q": "卡被冻结, 紧急", "is_p0": True, "p0_sub": "freeze"},
        {"q": "账户被锁, 怎么解锁", "is_p0": True, "p0_sub": "freeze"},
        {"q": "我的账户被冻结", "is_p0": True, "p0_sub": "freeze"},
        {"q": "为啥我的卡被冻", "is_p0": True, "p0_sub": "freeze"},
        {"q": "卡冻结怎么解", "is_p0": True, "p0_sub": "freeze"},
        {"q": "账户状态不对", "is_p0": True, "p0_sub": "freeze"},
        {"q": "卡状态异常", "is_p0": True, "p0_sub": "freeze"},
        {"q": "账户怎么锁住了", "is_p0": True, "p0_sub": "freeze"},
        {"q": "卡被封了, 怎么办", "is_p0": True, "p0_sub": "freeze"},
        {"q": "我的卡被锁了", "is_p0": True, "p0_sub": "freeze"},
        {"q": "账户被锁住", "is_p0": True, "p0_sub": "freeze"},
        {"q": "卡被冻了, 怎么解", "is_p0": True, "p0_sub": "freeze"},
        {"q": "为啥账户被锁", "is_p0": True, "p0_sub": "freeze"},
        {"q": "卡不能用了, 怎么解冻", "is_p0": True, "p0_sub": "freeze"},
    ],
    # ===== P0 第 4 类: sec_stolen_card (盗刷) - 20 条 =====
    "sec_stolen_card": [
        {"q": "收到陌生消费", "is_p0": True, "p0_sub": "stolen"},
        {"q": "收到陌生消费提醒", "is_p0": True, "p0_sub": "stolen"},
        {"q": "我没消费但卡被刷了", "is_p0": True, "p0_sub": "stolen"},
        {"q": "卡被刷 1000 元不是我", "is_p0": True, "p0_sub": "stolen"},
        {"q": "信用卡有笔消费不是我的", "is_p0": True, "p0_sub": "stolen"},
        {"q": "卡上有一笔陌生消费", "is_p0": True, "p0_sub": "stolen"},
        {"q": "陌生消费提醒", "is_p0": True, "p0_sub": "stolen"},
        {"q": "不是我的消费", "is_p0": True, "p0_sub": "stolen"},
        {"q": "盗刷", "is_p0": True, "p0_sub": "stolen"},
        {"q": "卡被刷了", "is_p0": True, "p0_sub": "stolen"},
        {"q": "被盗刷", "is_p0": True, "p0_sub": "stolen"},
        {"q": "陌生扣款", "is_p0": True, "p0_sub": "stolen"},
        {"q": "不是我的扣款", "is_p0": True, "p0_sub": "stolen"},
        {"q": "卡里少了钱, 不是我的", "is_p0": True, "p0_sub": "stolen"},
        {"q": "信用卡不是我的消费", "is_p0": True, "p0_sub": "stolen"},
        {"q": "卡被刷了 500 元", "is_p0": True, "p0_sub": "stolen"},
        {"q": "卡上扣了一笔不明的钱", "is_p0": True, "p0_sub": "stolen"},
        {"q": "卡被刷走 1000", "is_p0": True, "p0_sub": "stolen"},
        {"q": "信用卡被他人使用", "is_p0": True, "p0_sub": "stolen"},
        {"q": "卡上出现陌生交易", "is_p0": True, "p0_sub": "stolen"},
    ],
    # ===== P0 第 5 类: cons_urg_loss (紧急损失) - 15 条 =====
    "cons_urg_loss": [
        {"q": "刚被骗了怎么办", "is_p0": True, "p0_sub": "loss"},
        {"q": "卡丢了被刷了", "is_p0": True, "p0_sub": "loss"},
        {"q": "损失了 5 万, 紧急", "is_p0": True, "p0_sub": "loss"},
        {"q": "卡里钱都没了, 紧急", "is_p0": True, "p0_sub": "loss"},
        {"q": "我亏了 8 万, 紧急", "is_p0": True, "p0_sub": "loss"},
        {"q": "账户的钱被转走了, 紧急", "is_p0": True, "p0_sub": "loss"},
        {"q": "卡里钱突然没了", "is_p0": True, "p0_sub": "loss"},
        {"q": "被诈骗了, 紧急", "is_p0": True, "p0_sub": "loss"},
        {"q": "我亏了 10 万", "is_p0": True, "p0_sub": "loss"},
        {"q": "卡被盗, 钱没了", "is_p0": True, "p0_sub": "loss"},
        {"q": "我亏了钱, 紧急", "is_p0": True, "p0_sub": "loss"},
        {"q": "卡里钱少了, 紧急", "is_p0": True, "p0_sub": "loss"},
        {"q": "卡里的钱不见了, 紧急", "is_p0": True, "p0_sub": "loss"},
        {"q": "账户被扣款, 不是我的", "is_p0": True, "p0_sub": "loss"},
        {"q": "我卡里钱被转走了, 紧急", "is_p0": True, "p0_sub": "loss"},
    ],
    # ===== info_acc_balance - 15 条 =====
    "info_acc_balance": [
        {"q": "我卡里还有多少钱", "is_p0": False},
        {"q": "查询账户余额", "is_p0": False},
        {"q": "余额多少", "is_p0": False},
        {"q": "账户余额查询", "is_p0": False},
        {"q": "查下余额", "is_p0": False},
        {"q": "看下余额", "is_p0": False},
        {"q": "查一下账户余额", "is_p0": False},
        {"q": "我想查余额", "is_p0": False},
        {"q": "请问余额怎么查", "is_p0": False},
        {"q": "账户里有多少钱", "is_p0": False},
        {"q": "查下我账户余额", "is_p0": False},
        {"q": "活期账户余额", "is_p0": False},
        {"q": "我的账户还剩多少", "is_p0": False},
        {"q": "余额怎么查", "is_p0": False},
        {"q": "查询一下余额", "is_p0": False},
    ],
    # ===== info_bill_amount - 12 条 =====
    "info_bill_amount": [
        {"q": "我的信用卡账单多少", "is_p0": False},
        {"q": "这期账单金额", "is_p0": False},
        {"q": "信用卡账单金额", "is_p0": False},
        {"q": "查账单金额", "is_p0": False},
        {"q": "本期账单", "is_p0": False},
        {"q": "账单多少钱", "is_p0": False},
        {"q": "查这期账单", "is_p0": False},
        {"q": "信用卡账单多少", "is_p0": False},
        {"q": "查下账单金额", "is_p0": False},
        {"q": "账单金额多少", "is_p0": False},
        {"q": "我账单多少", "is_p0": False},
        {"q": "这月账单", "is_p0": False},
    ],
    # ===== info_bill_date - 10 条 =====
    "info_bill_date": [
        {"q": "什么时候还款", "is_p0": False},
        {"q": "最晚还款日", "is_p0": False},
        {"q": "还款日是哪天", "is_p0": False},
        {"q": "信用卡还款日", "is_p0": False},
        {"q": "我什么时候还", "is_p0": False},
        {"q": "这期还款日", "is_p0": False},
        {"q": "还款日怎么算", "is_p0": False},
        {"q": "查还款日", "is_p0": False},
        {"q": "还款日期", "is_p0": False},
        {"q": "什么时候到期", "is_p0": False},
    ],
    # ===== info_bill_point - 8 条 =====
    "info_bill_point": [
        {"q": "我有多少积分", "is_p0": False},
        {"q": "积分怎么查", "is_p0": False},
        {"q": "信用卡积分", "is_p0": False},
        {"q": "查下积分", "is_p0": False},
        {"q": "我的积分余额", "is_p0": False},
        {"q": "积分余额", "is_p0": False},
        {"q": "怎么查积分", "is_p0": False},
        {"q": "信用卡积分多少", "is_p0": False},
    ],
    # ===== info_tran_record - 10 条 =====
    "info_tran_record": [
        {"q": "查一下交易明细", "is_p0": False},
        {"q": "最近的交易记录", "is_p0": False},
        {"q": "我的消费明细", "is_p0": False},
        {"q": "交易流水", "is_p0": False},
        {"q": "查下交易记录", "is_p0": False},
        {"q": "信用卡交易明细", "is_p0": False},
        {"q": "我的交易明细", "is_p0": False},
        {"q": "查消费记录", "is_p0": False},
        {"q": "最近的消费", "is_p0": False},
        {"q": "看交易明细", "is_p0": False},
    ],
    # ===== info_branch - 8 条 =====
    "info_branch": [
        {"q": "招行网点在哪", "is_p0": False},
        {"q": "附近的招行", "is_p0": False},
        {"q": "招行营业网点", "is_p0": False},
        {"q": "查附近网点", "is_p0": False},
        {"q": "最近的招行", "is_p0": False},
        {"q": "招行在哪", "is_p0": False},
        {"q": "附近招行", "is_p0": False},
        {"q": "找招行网点", "is_p0": False},
    ],
    # ===== info_phone - 8 条 =====
    "info_phone": [
        {"q": "招行电话多少", "is_p0": False},
        {"q": "95555 怎么打", "is_p0": False},
        {"q": "招行客服电话", "is_p0": False},
        {"q": "95555 客服", "is_p0": False},
        {"q": "信用卡客服电话", "is_p0": False},
        {"q": "招行热线", "is_p0": False},
        {"q": "招行客服热线", "is_p0": False},
        {"q": "怎么联系招行", "is_p0": False},
    ],
    # ===== biz_card_activate - 10 条 =====
    "biz_card_activate": [
        {"q": "怎么激活信用卡", "is_p0": False},
        {"q": "新卡怎么开卡", "is_p0": False},
        {"q": "激活信用卡", "is_p0": False},
        {"q": "信用卡激活方法", "is_p0": False},
        {"q": "新卡激活", "is_p0": False},
        {"q": "怎么开卡", "is_p0": False},
        {"q": "卡怎么激活", "is_p0": False},
        {"q": "信用卡怎么激活", "is_p0": False},
        {"q": "新信用卡怎么开", "is_p0": False},
        {"q": "激活新卡", "is_p0": False},
    ],
    # ===== biz_card_loss - 8 条 =====
    "biz_card_loss": [
        {"q": "信用卡丢了怎么办", "is_p0": False},
        {"q": "挂失信用卡", "is_p0": False},
        {"q": "信用卡丢失", "is_p0": False},
        {"q": "卡丢了怎么办", "is_p0": False},
        {"q": "信用卡挂失", "is_p0": False},
        {"q": "怎么挂失", "is_p0": False},
        {"q": "我要挂失", "is_p0": False},
        {"q": "信用卡丢了", "is_p0": False},
    ],
    # ===== biz_card_reissue - 6 条 =====
    "biz_card_reissue": [
        {"q": "补办新卡", "is_p0": False},
        {"q": "补卡", "is_p0": False},
        {"q": "怎么补办信用卡", "is_p0": False},
        {"q": "信用卡补办", "is_p0": False},
        {"q": "补办新信用卡", "is_p0": False},
        {"q": "我要补办卡", "is_p0": False},
    ],
    # ===== biz_pwd_reset - 8 条 =====
    "biz_pwd_reset": [
        {"q": "密码忘了, 怎么重置", "is_p0": False},
        {"q": "重置密码", "is_p0": False},
        {"q": "忘记密码怎么办", "is_p0": False},
        {"q": "密码忘了", "is_p0": False},
        {"q": "怎么重置密码", "is_p0": False},
        {"q": "我要重置密码", "is_p0": False},
        {"q": "信用卡密码忘了", "is_p0": False},
        {"q": "忘记网银密码", "is_p0": False},
    ],
    # ===== biz_pwd_change - 5 条 =====
    "biz_pwd_change": [
        {"q": "怎么改密码", "is_p0": False},
        {"q": "修改密码", "is_p0": False},
        {"q": "改密码", "is_p0": False},
        {"q": "怎么修改密码", "is_p0": False},
        {"q": "我要改密码", "is_p0": False},
    ],
    # ===== biz_tran_limit - 8 条 =====
    "biz_tran_limit": [
        {"q": "转账限额多少", "is_p0": False},
        {"q": "单笔能转多少", "is_p0": False},
        {"q": "转账限额", "is_p0": False},
        {"q": "限额多少", "is_p0": False},
        {"q": "日转账限额", "is_p0": False},
        {"q": "单日限额", "is_p0": False},
        {"q": "最多能转多少", "is_p0": False},
        {"q": "转账能转多少", "is_p0": False},
    ],
    # ===== biz_pay_repay - 8 条 =====
    "biz_pay_repay": [
        {"q": "怎么还款", "is_p0": False},
        {"q": "主动还款怎么操作", "is_p0": False},
        {"q": "信用卡还款", "is_p0": False},
        {"q": "我要还款", "is_p0": False},
        {"q": "怎么还钱", "is_p0": False},
        {"q": "如何还款", "is_p0": False},
        {"q": "还款方法", "is_p0": False},
        {"q": "还款怎么弄", "is_p0": False},
    ],
    # ===== biz_installment - 6 条 =====
    "biz_installment": [
        {"q": "怎么分期", "is_p0": False},
        {"q": "账单分期手续费", "is_p0": False},
        {"q": "信用卡分期", "is_p0": False},
        {"q": "分期付款", "is_p0": False},
        {"q": "如何分期", "is_p0": False},
        {"q": "我要分期", "is_p0": False},
    ],
    # ===== sales_wealth_prod - 10 条 =====
    "sales_wealth_prod": [
        {"q": "有什么好理财", "is_p0": False},
        {"q": "理财推荐", "is_p0": False},
        {"q": "朝朝宝怎么样", "is_p0": False},
        {"q": "理财产品", "is_p0": False},
        {"q": "招行理财", "is_p0": False},
        {"q": "稳健理财", "is_p0": False},
        {"q": "高收益理财", "is_p0": False},
        {"q": "理财哪款好", "is_p0": False},
        {"q": "想了解理财", "is_p0": False},
        {"q": "朝朝宝收益", "is_p0": False},
    ],
    # ===== sales_credit_prod - 8 条 =====
    "sales_credit_prod": [
        {"q": "办什么信用卡好", "is_p0": False},
        {"q": "推荐一张信用卡", "is_p0": False},
        {"q": "招行信用卡", "is_p0": False},
        {"q": "办信用卡", "is_p0": False},
        {"q": "推荐信用卡", "is_p0": False},
        {"q": "哪张信用卡好", "is_p0": False},
        {"q": "想办信用卡", "is_p0": False},
        {"q": "信用卡推荐", "is_p0": False},
    ],
    # ===== sales_loan_prod - 6 条 =====
    "sales_loan_prod": [
        {"q": "招行信用贷", "is_p0": False},
        {"q": "贷款产品", "is_p0": False},
        {"q": "招行贷款", "is_p0": False},
        {"q": "信用贷款", "is_p0": False},
        {"q": "贷款推荐", "is_p0": False},
        {"q": "借点钱", "is_p0": False},
    ],
    # ===== cons_prod_credit - 6 条 =====
    "cons_prod_credit": [
        {"q": "申请信用卡", "is_p0": False},
        {"q": "怎么申请信用卡", "is_p0": False},
        {"q": "信用卡申请", "is_p0": False},
        {"q": "想申请信用卡", "is_p0": False},
        {"q": "信用卡怎么办", "is_p0": False},
        {"q": "如何办信用卡", "is_p0": False},
    ],
    # ===== cons_prod_loan - 5 条 =====
    "cons_prod_loan": [
        {"q": "贷款怎么办", "is_p0": False},
        {"q": "怎么贷款", "is_p0": False},
        {"q": "贷款申请", "is_p0": False},
        {"q": "想贷款", "is_p0": False},
        {"q": "如何贷款", "is_p0": False},
    ],
    # ===== cons_prod_wealth - 5 条 =====
    "cons_prod_wealth": [
        {"q": "理财产品推荐", "is_p0": False},
        {"q": "理财咨询", "is_p0": False},
        {"q": "想了解理财", "is_p0": False},
        {"q": "如何理财", "is_p0": False},
        {"q": "理财怎么办", "is_p0": False},
    ],
    # ===== cons_comp_service - 6 条 =====
    "cons_comp_service": [
        {"q": "我要投诉", "is_p0": False},
        {"q": "客服态度差", "is_p0": False},
        {"q": "服务质量差", "is_p0": False},
        {"q": "投诉处理", "is_p0": False},
        {"q": "服务投诉", "is_p0": False},
        {"q": "对服务不满意", "is_p0": False},
    ],
    # ===== sys_greeting - 6 条 =====
    "sys_greeting": [
        {"q": "你好", "is_p0": False},
        {"q": "您好, 我有问题咨询", "is_p0": False},
        {"q": "在吗", "is_p0": False},
        {"q": "您好", "is_p0": False},
        {"q": "hi", "is_p0": False},
        {"q": "你好, 在吗", "is_p0": False},
    ],
    # ===== sys_bye - 4 条 =====
    "sys_bye": [
        {"q": "再见", "is_p0": False},
        {"q": "谢谢, 拜拜", "is_p0": False},
        {"q": "拜拜", "is_p0": False},
        {"q": "bye", "is_p0": False},
    ],
    # ===== sys_thanks - 4 条 =====
    "sys_thanks": [
        {"q": "谢谢", "is_p0": False},
        {"q": "非常感谢", "is_p0": False},
        {"q": "多谢", "is_p0": False},
        {"q": "thx", "is_p0": False},
    ],
}


# ============================================================
# 统计
# ============================================================
def get_seeds_count() -> Dict[str, int]:
    """获取每意图种子数"""
    return {intent: len(seeds) for intent, seeds in SEEDS_V355.items()}


def get_total_seeds() -> int:
    return sum(len(seeds) for seeds in SEEDS_V355.values())


def get_p0_seeds() -> List[Dict]:
    """获取所有 P0 种子"""
    p0 = []
    for seeds in SEEDS_V355.values():
        for s in seeds:
            if s.get("is_p0"):
                p0.append(s)
    return p0


# ============================================================
# L0 词典扩展 (v3.5.5 新增 14 词 -> 30 词)
# ============================================================
L0_KEYWORDS_V355 = [
    # 已有 (v3.5.1 14 词)
    "转人工", "需要人工服务", "找人工", "人工客服",
    "账户异常冻结", "账户异常", "账户被冻", "卡被冻", "卡冻结了",
    "收到陌生消费", "陌生消费", "不是我消费", "卡被刷了", "卡被刷",
    # 新增 (v3.5.5 16 词 - 覆盖口语化 P0)
    "账户怎么被冻", "账户被锁", "卡被锁", "卡不能用",
    "卡被冻住", "卡冻结怎么解", "账户状态异常", "账户怎么锁",
    "卡状态异常", "卡不能用了", "卡突然不能用",
    "被盗刷", "盗刷", "陌生扣款", "不是我的扣款",
    "卡里少了钱", "不是我的消费",
    "卡被封", "账户被封", "卡被锁住", "账户被锁住",
    "骗子", "诈骗", "骗了",
    "紧急", "钱没了", "钱被转走", "钱不见了",
]


# ============================================================
# 模板 (12 种 - 不再口语化过头, 保持清晰)
# ============================================================
TEMPLATES_CLEAR = [
    lambda q: q,  # 原句
    lambda q: "请问" + q,  # 加请问
    lambda q: q + "?",  # 加问号
    lambda q: "想问一下" + q,  # 加想问一下
    lambda q: q + "谢谢",  # 加谢谢
    lambda q: "你好, " + q,  # 加你好 (不口语化)
]
