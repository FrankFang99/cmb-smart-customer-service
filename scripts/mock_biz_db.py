"""
v3.13.0 MiniMax M2.7 LLM 生成答案
====================================
核心改动 (vs v3.12.2):
- gen_answer() 对非 P0/非纯数据查询调用 MiniMax M2.7 生成答案
- 不再是硬编码模板，是真正的 LLM 能力
- P0 红线 / 纯数据 (余额/账单/积分) 仍走 mock 模板 (不需要 LLM)

设计原则:
- P0 红线: 必须快, 不走 LLM, 走硬编码
- 纯数据查询: mock 数据, 不走 LLM (数字是假的, LLM 生成解释浪费 token)
- 其他所有: LLM 生成 (更自然、更个性化)

MiniMax M2.7 调用:
- base_url: https://api.minimaxi.com/v1
- endpoint: /chat/completions (OpenAI-compatible)
- model: MiniMax-M2.7
"""
import os
import random
import datetime
import json
from typing import Dict, List, Optional, Tuple

try:
    import httpx
    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False

# ============================================================
# MiniMax M2.7 LLM 调用
# ============================================================
def _load_env():
    """从 .env 加载配置"""
    env_path = r'D:\Learning\AI\面试\AI智能客服\.env'
    env = {}
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    k, v = line.split('=', 1)
                    env[k.strip()] = v.strip()
    return env

def _call_llm(user_query: str, intent: str) -> str:
    """
    调用 MiniMax M2.7 生成答案
    Returns: LLM 生成的文本 (失败时返回 None)
    """
    if not _HAS_HTTPX:
        print('[LLM] httpx not installed')
        return None

    env = _load_env()
    api_key = env.get('MINIMAX_API_KEY', '')
    base_url = env.get('MINIMAX_BASE_URL', 'https://api.minimaxi.com/v1')
    model = env.get('MINIMAX_MODEL', 'MiniMax-M2.7')

    if not api_key:
        print('[LLM] No API key')
        return None

    system_prompt = """你是一个专业、温暖、简洁的招商银行智能客服。

要求:
- 用 **加粗** 标注关键信息 (金额/日期/电话/网址)
- 回答控制在 150 字以内
- 语气: 专业但亲切, 像一个有经验的银行柜员
- 不知道就说不知道, 不要编造数据
- 遇到转账/盗刷/投诉等敏感问题, 引导转人工
- **不要输出思考过程, 只输出最终回答**
- 只能在知识范围内回答, 不要编造招行不存在的产品或政策"""

    url = f'{base_url.rstrip("/")}/chat/completions'
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }
    body = {
        'model': model,
        'max_tokens': 300,
        'temperature': 0.3,
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': f"用户问题: {user_query}\n意图: {intent}\n请生成回答:"}
        ]
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, headers=headers, json=body)
            if resp.status_code != 200:
                print(f'[LLM] status={resp.status_code}: {resp.text[:200]}')
                return None
            data = resp.json()
            choices = data.get('choices', [])
            if choices:
                text = choices[0]['message']['content'].strip()
                # 去掉 M2.7 thinking 标签
                import re
                text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
                return text
    except Exception as e:
        print(f'[LLM] Exception: {e}')
    return None


# ============================================================
# 1. 账户系统
# ============================================================
class AccountSystem:
    """模拟账户系统 - 返回余额/明细/开户行"""

    MOCK_CUSTOMERS = [
        {'id': 'C001', 'name': '张先生', 'card_no_tail': '8866', 'card_type': '金葵花卡'},
        {'id': 'C002', 'name': '李女士', 'card_no_tail': '5210', 'card_type': '一卡通'},
        {'id': 'C003', 'name': '王先生', 'card_no_tail': '3378', 'card_type': '钻石卡'},
        {'id': 'C004', 'name': '赵女士', 'card_no_tail': '9102', 'card_type': '信用卡金卡'},
        {'id': 'C005', 'name': '陈先生', 'card_no_tail': '4475', 'card_type': '信用卡白金卡'},
    ]

    @classmethod
    def get_balance(cls) -> str:
        cust = random.choice(cls.MOCK_CUSTOMERS)
        balance = round(random.uniform(1234.56, 98765.43), 2)
        return (
            f'{cust["name"]} 的{cust["card_type"]} (尾号{cust["card_no_tail"]}) 当前余额:\n'
            f'**{balance:,.2f} 元**\n\n'
            f'实时同步于 {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}\n'
            f'数据来源: 账户系统 (AccountCore)'
        )

    @classmethod
    def get_recent_transactions(cls, n: int = 5) -> str:
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

    @classmethod
    def get_bill_amount(cls) -> str:
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
        cust = random.choice(AccountSystem.MOCK_CUSTOMERS)
        points = random.randint(1234, 98765)
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
# 3. 营销系统
# ============================================================
class MarketingSystem:

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
# 4. RAG 知识库
# ============================================================
class KnowledgeBase:

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
# 5. 风险提示语
# ============================================================
RISK_DISCLOSURES = {
    'cons_prod_wealth': '⚠️ 理财有风险, 投资需谨慎。过往业绩不预示未来表现。',
    'cons_prod_loan': '⚠️ 贷款需评估还款能力, 请合理规划负债率 (建议 ≤ 50%)。',
    'biz_transfer_large': '⚠️ 大额转账请确认收款方身份, 警惕冒充公检法 / 客服的诈骗。',
    'biz_installment': '⚠️ 分期手续费约 0.6%-0.8%/月, 请评估实际成本。',
}


# ============================================================
# 意图分类: 哪些走 LLM, 哪些走模板
# ============================================================
# 走 mock 模板 (纯数据查询, P0 红线, 必须快)
TEMPLATE_ONLY_INTENTS = {
    # 纯数据查询
    'info_acc_balance', 'info_tran_record', 'info_bill_amount',
    'info_bill_point', 'info_credit_limit',
    # RAG 知识库
    'info_branch', 'info_phone', 'biz_card_activate', 'biz_card_loss', 'biz_pay_repay',
    # 汇率 (mock 数据)
    'sys_fx_rate',
    # P0 红线 (必须快, 不能等 LLM)
    'cons_urg_human', 'sec_fraud_report', 'sec_stolen_card',
    'safety_card_loss', 'safety_card_freeze',
    'security_aml_large_transfer', 'biz_transfer_large',
    'cons_comp_service',
}

# 走 LLM (对话类, 需要自然语言生成)
LLM_ENABLED_INTENTS = {
    # 闲聊
    'sys_greeting', 'sys_service_greeting', 'sys_intro',
    'sys_bye', 'sys_service_farewell', 'sys_thanks',
    'sys_weather',  # L2 embedding 召回的天气类
    # 营销
    'mkt_food_5off', 'mkt_cinema_99', 'cons_prod_wealth',
    # 投诉 / 服务
    'sys_service_complaint',
    # 关键词 fallback 兜不住的情况
    'sys_invalid',
}


# ============================================================
# 主入口: gen_answer(intent, query) -> (answer, data_sources)
# ============================================================
def gen_answer(intent: str, query: str) -> Tuple[str, List[str]]:
    """
    根据意图 + 查询内容, 生成最终用户答案

    策略:
    - P0 红线 / 纯数据查询 → mock 模板 (快)
    - 闲聊 / 营销 / 投诉 / 天气 → MiniMax M2.7 生成 (真 AI)
    - LLM 失败时 fallback 到 mock 模板
    """

    # ---------- P0 红线 / 纯数据 → mock 模板 ----------
    if intent in TEMPLATE_ONLY_INTENTS:
        return _template_answer(intent, query)

    # ---------- 闲聊/营销/天气/投诉 → LLM ----------
    if intent in LLM_ENABLED_INTENTS:
        answer = _call_llm(query, intent)
        if answer:
            sources = ['MiniMax M2.7 LLM 生成']
            # 营销类加数据源标签
            if intent in ('mkt_food_5off', 'mkt_cinema_99', 'cons_prod_wealth'):
                sources.append('营销系统 (MktCore)')
                risk = RISK_DISCLOSURES.get(intent)
                if risk:
                    answer += f'\n\n{risk}'
            elif intent == 'sys_weather':
                sources.append('天气类-闲聊 (WeatherChat)')
            return answer, sources
        # LLM 失败 fallback 到模板
        return _template_answer(intent, query)

    # ---------- 关键词兜底 → LLM ----------
    keyword_answer = _keyword_fallback(query)
    if keyword_answer:
        answer, sources = keyword_answer
        # 尝试 LLM 生成更自然的版本
        llm_answer = _call_llm(query, intent)
        if llm_answer:
            return llm_answer, sources
        return answer, sources

    # ---------- 真兜底 → LLM ----------
    answer = _call_llm(query, intent)
    if answer:
        return answer, ['MiniMax M2.7 LLM (兜底)']
    return (
        '您的问题已记录, 正在为您转接人工客服...\n\n'
        '🔒 您的会话已加密\n'
        '📞 紧急情况请拨 95555'
    ), ['人工坐席系统 (HumanAgent)']


def _template_answer(intent: str, query: str) -> Tuple[str, List[str]]:
    """Mock 模板答案 (纯数据 / P0 红线)"""
    # ---- P0 转人工 ----
    if intent in ('cons_urg_human', 'sys_service_route_human'):
        return (
            '正在为您转接人工客服, 请稍候 (预计等待 30 秒)...\n\n'
            '🔒 您的会话已加密, 可放心描述问题\n'
            '📞 紧急情况请拨 95555'
        ), ['人工坐席系统 (HumanAgent)']

    # ---- P0 投诉 ----
    if intent in ('cons_comp_service', 'sys_service_complaint'):
        return (
            '非常抱歉给您带来不便, 我已记录您的反馈:\n\n'
            '  - 反馈类型: 服务投诉\n'
            '  - 跟进方式: 24 小时内专人回电\n'
            '  - 紧急通道: 转人工客服\n\n'
            '正在为您转接值班经理...'
        ), ['客服系统 (ServiceCore)', '人工坐席系统 (HumanAgent)']

    # ---- P0 风控 ----
    if intent in ('sec_fraud_report', 'sec_stolen_card', 'safety_card_loss',
                  'safety_card_freeze', 'sys_service_complaint'):
        return (
            '🚨 检测到紧急情况, 立即为您转接风控专员...\n\n'
            '请保持电话畅通, 我们的反欺诈专员会:\n'
            '  1. 核实账户异常交易\n'
            '  2. 协助冻结/挂失卡片\n'
            '  3. 引导报警 (如需)\n\n'
            '⏱️ 紧急通道: 0 等待\n'
            '📞 同时建议您拨 110 报警'
        ), ['风控系统 (RiskCore)', '反欺诈系统 (AntiFraud)', '人工坐席系统 (HumanAgent)']

    # ---- P0 AML ----
    if intent in ('security_aml_large_transfer', 'biz_transfer_large'):
        return (
            '🚨 大额转账 (≥ 5 万元) 已触发反洗钱风控:\n\n'
            '  1. 客服将致电核实转账目的\n'
            '  2. 可能要求提供: 收款人身份证 / 转账用途证明\n'
            '  3. 24 小时内未核实将延迟到账\n\n'
            '正在为您转接反洗钱专员...'
        ), ['反洗钱系统 (AML)', '风控系统 (RiskCore)', '人工坐席系统 (HumanAgent)']

    # ---- 账户系统 ----
    if intent == 'info_acc_balance':
        return AccountSystem.get_balance(), ['账户系统 (AccountCore)']
    if intent == 'info_tran_record':
        return AccountSystem.get_recent_transactions(), ['账户系统 (AccountCore)']

    # ---- 信用卡系统 ----
    if intent == 'info_bill_amount':
        return CreditCardSystem.get_bill_amount(), ['信用卡系统 (CardCore)']
    if intent == 'info_bill_point':
        return CreditCardSystem.get_points(), ['信用卡系统 (CardCore)']
    if intent == 'info_credit_limit':
        return CreditCardSystem.get_credit_limit(), ['信用卡系统 (CardCore)']

    # ---- RAG 知识库 ----
    if intent in ('info_branch', 'info_phone', 'biz_card_activate',
                  'biz_card_loss', 'biz_pay_repay', 'sys_fx_rate'):
        kb = KnowledgeBase.find_by_intent(intent)
        if kb:
            sources = ['RAG 知识库 (KB)']
            if intent == 'info_branch':
                sources.append('网点系统 (BranchCore)')
            elif intent == 'sys_fx_rate':
                sources.append('金融市场系统 (FXCore)')
            elif intent == 'biz_card_activate':
                sources.append('信用卡系统 (CardCore)')
            elif intent == 'biz_card_loss':
                sources = ['信用卡系统 (CardCore)', '风控系统 (RiskCore)']
            elif intent == 'biz_pay_repay':
                sources.append('支付系统 (PayCore)')
            return kb['answer'], sources

    # ---- 闲聊模板 fallback ----
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

    if intent == 'sys_intro':
        return (
            '我是**招行智能客服 "小招"**, 基于 4 层 Cascade 架构:\n\n'
            '  - **L0 红线词典**: 银行业强约束 (盗刷 / 转人工 / 投诉)\n'
            '  - **L1 业务规则**: 100+ 关键词模式\n'
            '  - **L2 BERT 分类 + Embedding 召回**: 30 + 3 label\n'
            '  - **L3 LLM 兜底**: MiniMax M2.7\n\n'
            '我能帮您查余额 / 账单 / 积分, 也能办激活 / 还款 / 转账。'
        ), ['闲聊系统 (ChatCore)', 'L2 BERT embedding 召回']

    # ---- 营销模板 fallback ----
    if intent in ('mkt_food_5off', 'mkt_cinema_99', 'cons_prod_wealth'):
        answer = MarketingSystem.get_marketing_answer(intent)
        if answer:
            sources = ['营销系统 (MktCore)']
            if intent == 'cons_prod_wealth':
                sources.append('理财系统 (WealthCore)')
            risk = RISK_DISCLOSURES.get(intent)
            if risk:
                answer += f'\n\n{risk}'
            return answer, sources

    return '', []


def _keyword_fallback(query: str) -> Optional[Tuple[str, List[str]]]:
    """关键词 fallback (最后兜底, 如果 LLM 失败走这里)"""
    q = query.lower()

    if any(k in query for k in ['汇率', '外汇', '美元', '欧元', '日元', '港币', '英镑']):
        kb = KnowledgeBase.find_by_intent('sys_fx_rate')
        if kb:
            return kb['answer'], ['金融市场系统 (FXCore)', 'RAG 知识库 (KB)']

    if any(k in query for k in ['网点', '地址', '在哪', '营业厅', '95555', '客服电话']):
        kb = KnowledgeBase.find_by_intent('info_phone')
        if kb:
            return kb['answer'], ['RAG 知识库 (KB)', '网点系统 (BranchCore)']

    if any(k in query for k in ['理财', '基金', '朝朝宝', '稳健', '高收益']):
        ans = MarketingSystem.get_marketing_answer('cons_prod_wealth')
        if ans:
            return ans + '\n\n⚠️ 理财有风险, 投资需谨慎。', ['理财系统 (WealthCore)', '营销系统 (MktCore)']

    return None


# ============================================================
# 测试入口
# ============================================================
if __name__ == '__main__':
    tests = [
        ('sys_greeting', '你好'),
        ('sys_intro', '你是谁'),
        ('sys_weather', '北京天气怎么样'),
        ('mkt_food_5off', '周三5折怎么用'),
        ('cons_prod_wealth', '有什么理财推荐'),
        ('cons_comp_service', '我要投诉'),
        ('sys_bye', '再见'),
    ]
    print('=== LLM 生成测试 ===\n')
    for intent, q in tests:
        ans, sources = gen_answer(intent, q)
        print(f'[Q: {q}] (intent={intent})')
        print(f'answer: {ans[:120]}...' if len(ans) > 120 else f'answer: {ans}')
        print(f'sources: {sources}')
        print('-' * 60)
