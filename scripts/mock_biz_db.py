"""
v3.12.2 Mock 业务数据库
========================
模拟招行 4 大核心业务系统, 给 Demo 提供真实可读的答案
没有真实 DB 接入, 但数据结构 + 字段命名 跟生产一致

4 个系统:
1. 账户系统 (Account System)    -> info_acc_balance / info_acc_detail
2. 信用卡系统 (Credit Card System) -> info_bill_amount / info_bill_point / biz_card_*
3. 营销系统 (Marketing System)    -> mkt_* / sales_*
4. RAG 知识库 (Knowledge Base)   -> info_branch / info_phone / cons_*

每个 intent 标注它依赖的 data_source (给 routing 面板展示)
"""
import random
import datetime
from typing import Dict, List, Optional, Tuple


# ============================================================
# 1. 账户系统
# ============================================================
class AccountSystem:
    """模拟账户系统 - 返回余额/明细/开户行"""

    # 模拟客户库 (5 个 mock 客户, 给 demo 用)
    MOCK_CUSTOMERS = [
        {'id': 'C001', 'name': '张先生', 'card_no_tail': '8866', 'card_type': '金葵花卡'},
        {'id': 'C002', 'name': '李女士', 'card_no_tail': '5210', 'card_type': '一卡通'},
        {'id': 'C003', 'name': '王先生', 'card_no_tail': '3378', 'card_type': '钻石卡'},
        {'id': 'C004', 'name': '赵女士', 'card_no_tail': '9102', 'card_type': '信用卡金卡'},
        {'id': 'C005', 'name': '陈先生', 'card_no_tail': '4475', 'card_type': '信用卡白金卡'},
    ]

    @classmethod
    def get_balance(cls) -> str:
        """查询余额 - 返回有真实数字的答案"""
        # 随机选一个 mock 客户
        cust = random.choice(cls.MOCK_CUSTOMERS)
        balance = round(random.uniform(1234.56, 98765.43), 2)
        return (
            f'您的{cust["card_type"]} (尾号{cust["card_no_tail"]}) 当前余额:\n'
            f'**{balance:,.2f} 元**\n\n'
            f'实时同步于 {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}\n'
            f'数据来源: 账户系统 (AccountCore)'
        )

    @classmethod
    def get_recent_transactions(cls, n: int = 5) -> str:
        """查询最近交易"""
        cust = random.choice(cls.MOCK_CUSTOMERS)
        lines = [f'{cust["name"]} 最近 {n} 笔交易 (尾号{cust["card_no_tail"]}):']
        merchants = ['星巴克', '美团', '京东商城', '中石化加油站', '盒马鲜生', '滴滴出行', '麦当劳', '沃尔玛']
        for i in range(n):
            days_ago = random.randint(0, 30)
            date = (datetime.datetime.now() - datetime.timedelta(days=days_ago)).strftime('%m-%d')
            amount = round(random.uniform(-200, -15) if random.random() > 0.2 else random.uniform(500, 5000), 2)
            lines.append(f'  {date}  {random.choice(merchants):8s}  ¥{amount:+,.2f}')
        lines.append(f'\n数据来源: 账户系统 (AccountCore) - 交易明细表')
        return '\n'.join(lines)


# ============================================================
# 2. 信用卡系统
# ============================================================
class CreditCardSystem:
    """模拟信用卡系统 - 返回账单/积分/额度"""

    @classmethod
    def get_bill_amount(cls) -> str:
        """本期账单"""
        cust = random.choice(AccountSystem.MOCK_CUSTOMERS)
        bill = round(random.uniform(1234.56, 9876.54), 2)
        min_pay = round(bill * 0.1, 2)
        due_date = (datetime.datetime.now().replace(day=1) + datetime.timedelta(days=49)).strftime('%Y-%m-%d')
        return (
            f'{cust["name"]} 的{cust["card_type"]} (尾号{cust["card_no_tail"]}) 本期账单:\n\n'
            f'  本期应还金额: **¥{bill:,.2f}**\n'
            f'  最低还款额:   ¥{min_pay:,.2f}\n'
            f'  最后还款日:   {due_date}\n\n'
            f'💡 按时还款可累积信用, 最低还款将产生利息\n'
            f'数据来源: 信用卡系统 (CardCore) - 账单表'
        )

    @classmethod
    def get_points(cls) -> str:
        """积分查询"""
        cust = random.choice(AccountSystem.MOCK_CUSTOMERS)
        points = random.randint(1234, 98765)
        # 积分兑换示例
        options = [
            ('星巴克中杯', 8800),
            ('视频网站月卡', 6000),
            ('20元话费', 2000),
            ('里程兑换 (1000 公里)', 15000),
        ]
        lines = [
            f'{cust["name"]} 的{cust["card_type"]} 当前积分:\n',
            f'  可用积分: **{points:,} 分**\n',
            '可兑换好礼:',
        ]
        for gift, cost in options:
            enough = '✓' if points >= cost else '○'
            lines.append(f'  {enough} {gift:20s} {cost:,} 分')
        lines.append(f'\n数据来源: 信用卡系统 (CardCore) - 积分账户')
        return '\n'.join(lines)

    @classmethod
    def get_credit_limit(cls) -> str:
        """额度查询"""
        cust = random.choice(AccountSystem.MOCK_CUSTOMERS)
        total_limit = random.choice([30000, 50000, 80000, 150000])
        used = round(total_limit * random.uniform(0.1, 0.7), 2)
        avail = total_limit - used
        return (
            f'{cust["name"]} 的{cust["card_type"]} 额度信息:\n\n'
            f'  总额度:     ¥{total_limit:,}\n'
            f'  已用:       ¥{used:,.2f}\n'
            f'  可用:       **¥{avail:,.2f}**\n\n'
            f'💡 临时调整额度: 1-3 个月, 拨打 95555 转人工\n'
            f'数据来源: 信用卡系统 (CardCore) - 额度表'
        )


# ============================================================
# 3. 营销系统 (活动 + 推荐)
# ============================================================
class MarketingSystem:
    """模拟营销系统 - 返回活动信息 + 推荐"""

    ACTIVE_CAMPAIGNS = [
        {
            'name': '周三 5 折饭票',
            'period': '2026-01 ~ 2026-12 (每周三)',
            'discount': '5 折',
            'merchants': ['麦当劳', '肯德基', '星巴克', '必胜客'],
            'rule': '每周三 10:00-22:00, 招行 App 饭票区抢购, 单笔最高减 30 元',
        },
        {
            'name': '影票 9.9 元',
            'period': '2026-03 ~ 2026-12 (档期)',
            'discount': '9.9 元起',
            'merchants': ['万达影城', 'CGV', '金逸影城'],
            'rule': '每周五/六/日 10:00 上线, 数量有限, 单卡限购 2 张',
        },
        {
            'name': '理财节加息',
            'period': '2026-06-15 ~ 2026-07-15',
            'discount': '+0.5% 加息券',
            'merchants': ['朝朝宝', '稳健理财'],
            'rule': '首次购买 1 万+ 30 天以上产品, 可领 0.5% 加息券',
        },
    ]

    @classmethod
    def get_marketing_answer(cls, intent: str) -> str:
        """营销类 query"""
        if intent == 'mkt_food_5off':
            c = cls.ACTIVE_CAMPAIGNS[0]
            return (
                f'【周三 5 折饭票】活动详情:\n\n'
                f'  活动期: {c["period"]}\n'
                f'  折扣:   {c["discount"]}\n'
                f'  适用:   {", ".join(c["merchants"])}\n'
                f'  规则:   {c["rule"]}\n\n'
                f'📱 抢购入口: 招商银行 App → 首页 → 饭票\n'
                f'数据来源: 营销系统 (MktCore) - 活动表'
            )
        if intent == 'mkt_cinema_99':
            c = cls.ACTIVE_CAMPAIGNS[1]
            return (
                f'【影票 9.9 元】活动详情:\n\n'
                f'  活动期: {c["period"]}\n'
                f'  折扣:   {c["discount"]}\n'
                f'  适用:   {", ".join(c["merchants"])}\n'
                f'  规则:   {c["rule"]}\n\n'
                f'📱 抢购入口: 招商银行 App → 首页 → 影票\n'
                f'数据来源: 营销系统 (MktCore) - 活动表'
            )
        if intent == 'cons_prod_wealth':
            c = cls.ACTIVE_CAMPAIGNS[2]
            return (
                f'【理财节加息】活动详情:\n\n'
                f'  活动期: {c["period"]}\n'
                f'  加息:   {c["discount"]}\n'
                f'  适用:   {", ".join(c["merchants"])}\n'
                f'  规则:   {c["rule"]}\n\n'
                f'💡 当前理财参考收益 (mock):\n'
                f'  朝朝宝 7 日年化: 1.85%\n'
                f'  稳健理财 30 天:  2.45%\n'
                f'  黄金 1 个月:      3.20% (非保本)\n\n'
                f'数据来源: 营销系统 (MktCore) + 理财系统 (WealthCore)'
            )
        return ''


# ============================================================
# 4. RAG 知识库 (网点 / 电话 / 规则咨询)
# ============================================================
class KnowledgeBase:
    """模拟 RAG 知识库 - 返回结构化知识"""

    KB = [
        {
            'intent': 'info_branch',
            'question': '附近招行网点',
            'answer': (
                '📍 招行网点查询 (mock 数据):\n\n'
                '  1. 佛山分行营业部\n'
                '     地址: 佛山市禅城区季华五路 30 号\n'
                '     营业时间: 周一至周五 9:00-17:00, 周六 9:30-16:00\n'
                '     电话: 0757-8398-1234\n\n'
                '  2. 禅城支行\n'
                '     地址: 佛山市禅城区祖庙路 28 号\n'
                '     营业时间: 周一至周五 9:00-17:00\n'
                '     电话: 0757-8123-4567\n\n'
                '  3. 顺德支行\n'
                '     地址: 佛山市顺德区大良街道德民路 15 号\n'
                '     营业时间: 周一至周五 9:00-17:00\n\n'
                '💡 实时查询: 招行 App → 网点预约, 或拨 95555\n'
                '数据来源: RAG 知识库 (KB) + 网点系统 (BranchCore)'
            ),
        },
        {
            'intent': 'info_phone',
            'question': '招行客服电话',
            'answer': (
                '📞 招行客户服务热线:\n\n'
                '  信用卡客服: **95555** (7×24)\n'
                '  一卡通客服: **95555** 转 1\n'
                '  贷款客服:   **40088-95555**\n'
                '  贵宾专线:   **40066-95555** (金葵花及以上)\n'
                '  境外服务:   **+86-755-8319-5555**\n\n'
                '💡 智能客服 7×24 在线, 人工坐席 8:00-22:00\n'
                '数据来源: RAG 知识库 (KB) - 客服联系表'
            ),
        },
        {
            'intent': 'biz_card_activate',
            'question': '信用卡激活',
            'answer': (
                '💳 信用卡激活方式:\n\n'
                '  1. **App 激活** (推荐)\n'
                '     招商银行 App → 信用卡 → 卡管理 → 激活\n'
                '     支持人脸识别, 1 分钟完成\n\n'
                '  2. **电话激活**\n'
                '     拨打 95555 → 信用卡 → 输入卡号 + 身份证号 → 设置查询密码\n\n'
                '  3. **网点激活**\n'
                '     持卡 + 身份证 到任意招行网点\n\n'
                '⚠️ 未激活卡片不能刷卡消费和取现\n'
                '数据来源: RAG 知识库 (KB) + 信用卡系统 (CardCore)'
            ),
        },
        {
            'intent': 'biz_card_loss',
            'question': '信用卡挂失',
            'answer': (
                '🚨 信用卡挂失流程 (紧急):\n\n'
                '  **步骤 1**: 立即拨打 95555 报失 (7×24)\n'
                '  **步骤 2**: 客服核实身份后冻结卡片\n'
                '  **步骤 3**: 申请补办新卡 (EMS 邮寄, 5-7 工作日)\n'
                '  **步骤 4**: 新卡激活后旧卡作废\n\n'
                '⚠️ 挂失后请立即:\n'
                '  - 检查最近交易, 异常交易将被协助处理\n'
                '  - 修改绑定该卡的第三方支付 (支付宝/微信等)\n'
                '  - 警惕后续诈骗电话\n\n'
                '🔒 数据来源: 信用卡系统 (CardCore) + 风控系统 (RiskCore)'
            ),
        },
        {
            'intent': 'biz_pay_repay',
            'question': '怎么还款',
            'answer': (
                '💰 信用卡还款方式:\n\n'
                '  1. **自动还款** (推荐, 避免逾期)\n'
                '     绑定一卡通, 每月自动扣款\n'
                '     App → 信用卡 → 还款管理 → 自动还款\n\n'
                '  2. **主动还款**\n'
                '     App → 信用卡 → 还款 → 输入金额\n'
                '     支持招行卡 / 他行卡 / 支付宝\n\n'
                '  3. **他行转账**\n'
                '     通过他行网银/手机银行向招行信用卡转账\n'
                '     备注卡号后 4 位\n\n'
                '⚠️ 跨行还款可能 1-2 工作日到账, 请预留时间\n'
                '数据来源: RAG 知识库 (KB) + 支付系统 (PayCore)'
            ),
        },
        {
            'intent': 'cons_urg_human',
            'question': '转人工',
            'answer': None,  # 走 P0 转人工
        },
        {
            'intent': 'sys_fx_rate',
            'question': '汇率查询',
            'answer': (
                '💱 主要币种汇率 (mock, 参考 2026-06-27):\n\n'
                '  美元 USD: 100 USD = **710.50** CNY\n'
                '  欧元 EUR: 100 EUR = **772.30** CNY\n'
                '  港币 HKD: 100 HKD = **91.20** CNY\n'
                '  日元 JPY: 100 JPY = **4.85** CNY\n'
                '  英镑 GBP: 100 GBP = **905.60** CNY\n\n'
                '💡 实时汇率请以中国银行外汇牌价为准\n'
                '💡 大额结汇 (≥ 5 万美元) 需要提前预约\n'
                '数据来源: 金融市场系统 (FXCore) + 中国银行牌价'
            ),
        },
    ]

    @classmethod
    def find_by_intent(cls, intent: str) -> Optional[dict]:
        for kb in cls.KB:
            if kb['intent'] == intent:
                return kb
        return None


# ============================================================
# 5. 风险提示语 (给理财 / 转账类业务用)
# ============================================================
RISK_DISCLOSURES = {
    'cons_prod_wealth': '⚠️ 理财有风险, 投资需谨慎。过往业绩不预示未来表现。',
    'cons_prod_loan': '⚠️ 贷款需评估还款能力, 请合理规划负债率 (建议 ≤ 50%)。',
    'biz_transfer_large': '⚠️ 大额转账请确认收款方身份, 警惕冒充公检法 / 客服的诈骗。',
    'biz_installment': '⚠️ 分期手续费约 0.6%-0.8%/月, 请评估实际成本。',
}


# ============================================================
# 主入口: genAnswer(intent, query) -> (answer, data_sources)
# ============================================================
def gen_answer(intent: str, query: str) -> Tuple[str, List[str]]:
    """
    根据意图 + 数据源, 生成最终用户答案

    Returns:
        (answer_text, data_sources_list)
        - answer_text: 真实可读的答案
        - data_sources_list: 接入的数据源列表 (给 routing 面板)
    """

    # ---------- 1. 账户系统 ----------
    if intent == 'info_acc_balance':
        return AccountSystem.get_balance(), ['账户系统 (AccountCore)']

    if intent == 'info_tran_record':
        return AccountSystem.get_recent_transactions(), ['账户系统 (AccountCore)']

    # ---------- 2. 信用卡系统 ----------
    if intent == 'info_bill_amount':
        return CreditCardSystem.get_bill_amount(), ['信用卡系统 (CardCore)']

    if intent == 'info_bill_point':
        return CreditCardSystem.get_points(), ['信用卡系统 (CardCore)']

    if intent == 'info_credit_limit':
        return CreditCardSystem.get_credit_limit(), ['信用卡系统 (CardCore)']

    # ---------- 3. 业务办理 ----------
    if intent == 'biz_card_activate':
        kb = KnowledgeBase.find_by_intent(intent)
        return kb['answer'], ['RAG 知识库 (KB)', '信用卡系统 (CardCore)']

    if intent == 'biz_card_loss':
        kb = KnowledgeBase.find_by_intent(intent)
        return kb['answer'], ['信用卡系统 (CardCore)', '风控系统 (RiskCore)']

    if intent == 'biz_pay_repay':
        kb = KnowledgeBase.find_by_intent(intent)
        return kb['answer'], ['RAG 知识库 (KB)', '支付系统 (PayCore)']

    # ---------- 4. 营销 / 推荐 ----------
    if intent in ('mkt_food_5off', 'mkt_cinema_99', 'cons_prod_wealth'):
        answer = MarketingSystem.get_marketing_answer(intent)
        if answer:
            sources = ['营销系统 (MktCore)']
            if intent == 'cons_prod_wealth':
                sources.append('理财系统 (WealthCore)')
            # 加风险提示
            risk = RISK_DISCLOSURES.get(intent)
            if risk:
                answer += f'\n\n{risk}'
            return answer, sources

    # ---------- 5. RAG 知识库 ----------
    if intent in ('info_branch', 'info_phone', 'sys_fx_rate'):
        kb = KnowledgeBase.find_by_intent(intent)
        if kb:
            sources = ['RAG 知识库 (KB)']
            if intent == 'info_branch':
                sources.append('网点系统 (BranchCore)')
            elif intent == 'sys_fx_rate':
                sources.append('金融市场系统 (FXCore)')
            return kb['answer'], sources

    # ---------- 5b. 天气 (v3.12.2 L2 embedding 召回) ----------
    if intent == 'sys_weather':
        return (
            '我是招行智能客服, 天气查询我帮不上忙 😄\n\n'
            '我能帮您:\n'
            '  💰 查询余额 / 账单 / 积分\n'
            '  💳 信用卡激活 / 挂失 / 还款\n'
            '  📍 网点查询 / 客服电话\n'
            '  💱 实时汇率 (mock 数据)\n\n'
            '💡 推荐: 中国天气网 / 墨迹天气 / 苹果天气 App\n'
            '数据来源: L2 BERT embedding 召回 (天气类)'
        ), ['天气类-闲聊 (WeatherChat)']

    # ---------- 5c. 自我介绍 (v3.12.2 L2 embedding 召回) ----------
    if intent == 'sys_intro':
        return (
            '我是**招行智能客服 "小招"**, v3.12.2 版本, 基于 4 层 Cascade 架构:\n\n'
            '  - **L0 红线词典**: 银行业强约束 (盗刷 / 转人工 / 投诉)\n'
            '  - **L1 业务规则**: 100+ 关键词模式\n'
            '  - **L2 BERT 分类 + Embedding 召回**: 30 + 3 label\n'
            '  - **L3 LLM 兜底**: MiniMax M2.7 (含 thinking)\n\n'
            '我能帮您:\n'
            '  💰 查询余额 / 账单 / 积分\n'
            '  💳 信用卡激活 / 挂失 / 还款\n'
            '  📍 网点查询 / 客服电话\n'
            '  💱 实时汇率 (mock)\n\n'
            '数据来源: 4 大业务系统 (mock) + RAG 知识库'
        ), ['闲聊系统 (ChatCore)', 'L2 BERT embedding 召回']

    # ---------- 6. P0 转人工类 (不能给 AI 回复) ----------
    if intent in ('cons_urg_human', 'sys_service_route_human'):
        return (
            '正在为您转接人工客服, 请稍候 (预计等待 30 秒)...\n\n'
            '🔒 您的会话已加密, 可放心描述问题\n'
            '📞 紧急情况请拨 95555'
        ), ['人工坐席系统 (HumanAgent)']

    if intent in ('cons_comp_service', 'sys_service_complaint'):
        return (
            '非常抱歉给您带来不便, 我已记录您的反馈:\n\n'
            '  - 反馈类型: 服务投诉\n'
            '  - 跟进方式: 24 小时内专人回电\n'
            '  - 紧急通道: 转人工客服\n\n'
            '正在为您转接值班经理...'
        ), ['客服系统 (ServiceCore)', '人工坐席系统 (HumanAgent)']

    # 安全 / 风控 (P0)
    if intent in ('sec_fraud_report', 'sec_stolen_card', 'sec_freeze_unexpected',
                  'safety_card_loss', 'safety_card_freeze', 'sys_service_complaint'):
        return (
            '🚨 检测到紧急情况, 立即为您转接风控专员...\n\n'
            '请保持电话畅通, 我们的反欺诈专员会:\n'
            '  1. 核实账户异常交易\n'
            '  2. 协助冻结/挂失卡片\n'
            '  3. 引导报警 (如需)\n\n'
            '⏱️ 紧急通道: 0 等待\n'
            '📞 同时建议您拨 110 报警'
        ), ['风控系统 (RiskCore)', '反欺诈系统 (AntiFraud)', '人工坐席系统 (HumanAgent)']

    if intent in ('security_aml_large_transfer', 'biz_transfer_large'):
        return (
            '🚨 大额转账 (≥ 5 万元) 已触发反洗钱风控:\n\n'
            '  1. 客服将致电核实转账目的\n'
            '  2. 可能要求提供: 收款人身份证 / 转账用途证明\n'
            '  3. 24 小时内未核实将延迟到账\n\n'
            '正在为您转接反洗钱专员...'
        ), ['反洗钱系统 (AML)', '风控系统 (RiskCore)', '人工坐席系统 (HumanAgent)']

    # ---------- 7. 闲聊 ----------
    if intent in ('sys_greeting', 'sys_service_greeting'):
        return (
            '您好! 我是招行智能客服 "小招"\n\n'
            '我能帮您:\n'
            '  💰 查询余额 / 账单 / 积分\n'
            '  💳 信用卡激活 / 挂失 / 还款\n'
            '  📍 网点查询 / 客服电话\n'
            '  🎁 营销活动推荐\n\n'
            '请问今天想办理什么业务?'
        ), ['闲聊系统 (ChatCore)']

    if intent in ('sys_bye', 'sys_service_farewell', 'sys_thanks'):
        return '感谢您选择招商银行, 祝您生活愉快! 如有需要随时呼叫我 👋', ['闲聊系统 (ChatCore)']

    # ---------- 8. 关键词兜底 (intent=sys_invalid 时, 看 query 实际内容给答案) ----------
    # 这是 v3.12.2 关键改进: 不让 AI 假装"我不理解", 而是看用户真正问的是什么, 给合理答案
    keyword_answer = _keyword_fallback(query)
    if keyword_answer:
        return keyword_answer

    # ---------- 9. 真兜底 ----------
    return (
        '抱歉, 您的问题暂时不在我的能力范围内。\n\n'
        '建议:\n'
        '  - 换种方式描述您的需求\n'
        '  - 或输入 "转人工" 接入人工客服 (0 等待)\n'
        '  - 紧急情况请拨 95555\n\n'
        '🔔 我已记录本次问题, 将持续优化'
    ), ['意图识别失败 (建议转人工)']


def _keyword_fallback(query: str) -> Optional[Tuple[str, List[str]]]:
    """
    关键词兜底: 当 intent=sys_invalid 时, 看 query 里有没有已知的业务关键词
    这是反"规则驱动"的关键 - 不要让 AI 假装不理解, 而是尝试给出合理答案
    """
    q = query.lower()

    # 汇率
    if any(k in query for k in ['汇率', '外汇', '美元', '欧元', '日元', '港币', '英镑']):
        kb = KnowledgeBase.find_by_intent('sys_fx_rate')
        if kb:
            return kb['answer'], ['金融市场系统 (FXCore)', 'RAG 知识库 (KB)']

    # 天气 (闲聊兜底 - 不属于银行业务, 但要礼貌回复)
    if any(k in query for k in ['天气', '气温', '下雨', '下雪', '晴天']):
        return (
            '我是招行智能客服, 天气查询我帮不上忙 😄\n\n'
            '我可以帮您:\n'
            '  💰 查询余额 / 账单 / 积分\n'
            '  💳 信用卡激活 / 挂失 / 还款\n'
            '  📍 网点查询 / 客服电话\n'
            '  💱 实时汇率 (mock 数据)\n\n'
            '请试试银行业务相关的问题?'
        ), ['闲聊系统 (ChatCore)']

    # 时间/日期
    if any(k in query for k in ['几点', '今天几号', '日期', '现在时间', '星期几']):
        now = datetime.datetime.now()
        return (
            f'当前时间: {now.strftime("%Y-%m-%d %H:%M:%S")}\n'
            f'星期: {"一二三四五六日"[now.weekday()]}\n\n'
            '💡 银行业务问题我也很乐意帮忙~'
        ), ['闲聊系统 (ChatCore)']

    # 问候/自我介绍
    if any(k in query for k in ['你是谁', '叫什么', '介绍', '你是什么']):
        return (
            '我是**招行智能客服 "小招"**, v3.12.2 版本, 基于:\n\n'
            '  - **L0 红线词典**: 银行业强约束 (盗刷 / 转人工 / 投诉)\n'
            '  - **L1 业务规则**: 100+ 关键词模式\n'
            '  - **L2 BERT 分类**: 30 个意图, val_acc 99.65%\n'
            '  - **L3 LLM 兜底**: MiniMax M2.7 (含 thinking)\n\n'
            '我能帮您查余额 / 账单 / 积分, 也能办激活 / 还款 / 转账。\n'
            '数据来源包括 4 大业务系统 + RAG 知识库 (mock)。'
        ), ['闲聊系统 (ChatCore)']

    # 理财相关 (LLM 误判 sys_invalid 时兜底)
    if any(k in query for k in ['理财', '基金', '朝朝宝', '稳健', '高收益']):
        ans = MarketingSystem.get_marketing_answer('cons_prod_wealth')
        if ans:
            return ans + '\n\n⚠️ 理财有风险, 投资需谨慎。', ['理财系统 (WealthCore)', '营销系统 (MktCore)']

    # 网点 / 电话
    if any(k in query for k in ['网点', '地址', '在哪', '营业厅', '95555', '客服电话']):
        kb = KnowledgeBase.find_by_intent('info_phone')
        if kb:
            return kb['answer'], ['RAG 知识库 (KB)', '网点系统 (BranchCore)']

    return None


# ============================================================
# 测试入口
# ============================================================
if __name__ == '__main__':
    tests = [
        ('info_acc_balance', '卡里还有多少钱'),
        ('info_bill_amount', '本期账单多少'),
        ('info_bill_point', '我有多少积分'),
        ('info_credit_limit', '信用卡额度多少'),
        ('biz_card_activate', '信用卡怎么激活'),
        ('info_branch', '附近网点在哪'),
        ('info_phone', '客服电话多少'),
        ('mkt_food_5off', '周三 5 折怎么用'),
        ('cons_urg_human', '转人工'),
        ('cons_comp_service', '我要投诉'),
        ('sec_stolen_card', '卡被盗刷了'),
        ('sys_greeting', '你好'),
    ]
    for intent, q in tests:
        ans, sources = gen_answer(intent, q)
        print(f'=== Q: {q} (intent={intent}) ===')
        print(ans)
        print(f'\n数据源: {", ".join(sources)}')
        print('-' * 60)