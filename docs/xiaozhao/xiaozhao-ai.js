/**
 * v3.12.1 GitHub Page 前端 AI 引擎 (JS 重写版)
 * ====================================================
 * 真跑银行业 L0 红线词典 + L1 规则匹配 + 业务权重
 * 跟 Python IntentRecognizer 行为一致
 */

// ============================================================
// v3.12.1 ADVERSARIAL_L0_KEYWORDS (对抗性 P0 红线)
// ============================================================
const ADVERSARIAL_L0_KEYWORDS = {
  prompt_injection: [
    'ignore previous', 'ignore all', 'ignore the', 'ignore my',
    'ignore your', 'ignore everything', 'ignore above',
    'ignore prior', 'ignore instructions', 'ignore system',
    'forget previous', 'forget all', 'forget your', 'forget above',
    'forget the', 'forget instructions',
    'disregard previous', 'disregard all', 'disregard the',
    'disregard your', 'disregard safety', 'disregard instructions',
    'forget everything', 'forget all instructions', 'forget all rules',
    'override previous', 'override all', 'override the',
    'override system', 'override safety', 'override instructions',
    'bypass previous', 'bypass all', 'bypass safety', 'bypass security',
    'bypass instructions', 'bypass rules', 'bypass system',
    'skip previous', 'skip all', 'skip rules', 'skip safety',
    'end system prompt', 'new system', 'new instructions',
    'you are now', 'you must now', 'act as',
    'jailbreak', 'jail break', 'jail-break',
    'do anything now', 'developer mode', 'god mode',
    'system prompt', 'your prompt', 'your instructions',
    'your training', 'training data', 'your rules',
    'tell me your', 'show me your', 'reveal your',
    'what are your', 'what is your',
    'ignore previous instructions', 'ignore all instructions',
    'forget all instructions', 'disregard all instructions',
    'override system prompt', 'jailbreak mode', 'sudo rm',
    'as an ai you must',
    'admin mode', 'unlock all', 'unlock restrictions', 'unlock all restrictions',
    'developer mode', 'testing you', 'output your', 'full prompt',
    'follow regulation', 'follow banking', 'listen to me',
    'chatgpt', 'you are chatgpt', 'now chatgpt',
    'disregard safety', 'disregard guidelines', 'safety guidelines',
  ],
  phishing: [
    'click this link', 'click here', 'click the link',
    'scan this qr', 'scan the code', 'scan code',
    'click to claim', 'click to receive', 'click to get',
    'you have won', 'you won', 'you are the winner',
    'claim your prize', 'claim prize', 'claim reward',
    'send verification code', 'give me your code',
    'send me your code', 'tell me your code',
    'verify your identity', 'verify your account',
    'update your account', 'confirm your account',
    'reactivate your account', 'unlock your account',
    'your account is locked', 'your account has been',
    'your account will be', 'your card has been',
    'your card will be',
    'transfer to safe account', 'transfer to security account',
    'transfer to protected account', 'transfer to a safe',
    'transfer money to', 'transfer to my personal',
    'send money to', 'pay the fee', 'pay handling fee',
    'pay customs fee', 'pay tax fee', 'pay processing fee',
    'won 1 million', 'won 5 million', 'won a prize',
    'free iphone', 'free gift', 'free trial', 'free voucher',
    'congratulations you', 'congratulations on winning',
    'i am from cmb', 'i am from bank',
    'i am customer manager', 'i am account manager',
    'i am 110', 'i am from 110', 'i am from police',
    'i am from anti-fraud', 'i am from anti fraud',
    'i am from csrc', 'i am from cbirc',
    '点击链接', '扫码领取', '扫码支付', '扫码验证',
    '验证码告诉我', '验证码发我', '验证码给我',
    '涉嫌洗钱', '安全账户', '安全账号',
    '先打手续费', '支付邮费', '支付关税',
    '中奖了先付', '中奖先打款', '您已被抽中',
    '我是招行安全部门', '我是反诈中心',
    'give me your', 'give me your verification',
    'cmb security dept', 'security dept', 'card number and password',
    'medical insurance', 'insurance account', 'account abnormal',
    'package held by customs', 'held by customs', 'pay postage',
    'cmb points', 'points expire', 'redeem cash',
    'wife hotel records', 'hotel records',
    'car accident', 'transfer surgery fee', 'surgery fee',
    'son colleague', 'your son', 'immediate transfer',
  ],
  unauthorized: [
    'hack into', 'hack account', 'hack cmb',
    'crack the', 'crack code', 'crack password', 'crack verification',
    'steal password', 'steal verification', 'steal card number',
    'steal money', 'steal account', 'steal from',
    'forge card', 'fake card', 'counterfeit card',
    'fake work badge', 'fake employee', 'fake id',
    'fake website', 'fake cmb', 'fake app',
    'bypass regulation', 'bypass regulatory', 'bypass compliance',
    'bypass kyc', 'bypass aml', 'bypass audit',
    'bypass control', 'bypass limit', 'bypass limit on',
    'bypass verification', 'bypass authentication',
    'launder money', 'money laundering', 'clean money',
    'shell company', 'shell corp', 'fake company',
    'open account no real name', 'no real name account',
    'no kyc account', 'no verification account',
    'help me hack', 'help me forge', 'help me fake',
    'help me bypass', 'help me crack', 'help me steal',
    'tell me api key', 'give me api', 'show me api',
    'your api key', 'your training data', 'your weights',
    'your source code', 'your code', 'your model',
    '帮我黑', '帮我盗', '帮我破', '帮我洗',
    '绕过监管', '绕过审计', '绕过合规', '绕过反洗钱',
    '盗取密码', '盗刷', '盗账户',
    '洗钱', '洗干净钱', '洗钱方法',
    '皮包公司', '空壳公司', '壳公司',
    '不实名开户', '匿名账户', '实名不过',
    '违规操作', '违规转账', '绕过限额',
    '违规跨境', '绕过外汇管制',
    '你是你爸爸', '我是你爸爸', '听我的话',
    '听我的', '必须听我的', '必须办',
    '假工作证', '假工牌', '假身份证',
    '伪卡', '假卡', '克隆卡',
    'i am your father', 'you must listen', 'must listen to me',
    'cmb system', 'system vulnerability', 'cmb app bugs', 'app bugs',
    'phishing site', 'write a phishing', 'help me write',
    'pretend to be', 'pretend to be a human', 'you are a human',
    'steal others', 'steal bank card', 'steal card',
    'backdoor', 'his dad', 'dad is bank president',
    'i take legal', 'take legal responsibility',
    'no-real-name', 'no real name', 'allows no-real-name',
    'i am a hacker', 'attack cmb', 'help me attack',
  ],
  boundary_violation: [
    'how to kill', 'how to murder', 'how to assassinate',
    'kill someone', 'murder someone', 'kill my',
    'teach me to kill', 'help me kill',
    'how to suicide', 'how to commit suicide',
    'commit suicide', 'kill myself', 'end my life',
    'how to do drugs', 'how to make drugs',
    'make drugs', 'synthesize drugs',
    'how to gamble', 'how to cheat', 'how to fix',
    'match fixing', 'how to launder', 'how to bribe',
    'bribe officials', 'bribe police', 'bribe judges',
    'hack into computer', 'hack into phone',
    'write a virus', 'create malware', 'make ransomware',
    'find prostitute', 'find escort', 'buy drugs',
    'buy guns', 'buy weapons',
    'tax evasion', 'evade tax', 'evade taxes',
    'teach me to hack', 'teach me to crack',
    '怎么杀', '教我杀', '帮我杀', '杀人方法',
    '自杀方法', '怎么自杀', '我想死', '活不下去',
    '教我赌博', '怎么赌博', '赌博方法', '赌球',
    '教我吸毒', '怎么吸毒', '制毒方法',
    '教我黑', '黑客教程', '怎么入侵',
    '找小姐', '嫖娼', '卖淫',
    '怎么偷税', '偷税方法', '逃税方法',
    '写病毒', '制作病毒', '勒索病毒',
    '贿赂官员', '贿赂警察', '贿赂法官',
    '买枪', '买毒品', '军火',
    'how to get divorced', 'get divorced',
    'want to suicide', 'how to do it', 'how to suicide',
    'write virus', 'how to write', 'teach me how to write',
    'tax evade', 'tax evade without', 'evade without',
  ],
};

// ============================================================
// v3.12.0 P0 红线词典 (中文 + 银行业务)
// ============================================================
const FRAUD_KEYWORDS = {
  fake_identity: ['假冒', '冒充', '假装是', '自称是', '对方说是', '公安', '检察院', '法院', '法官', '检察官', '警察', '警官', '银保监', '银监会', '证监会', '央行', '客服', '官方', '工作人员', '客服电话', '银行工作人员', '工作人员让我', '客服让我'],
  fraud_high_risk: ['被骗', '被诈骗', '诈骗', '上当', '上当受骗', '被忽悠', '盗刷', '被盗', '被刷', '刷走了', '不认识的扣款', '不明扣款', '账户冻结', '卡被冻结', '账号被冻', '冻结了', '异常交易', '不是我的交易', '我没操作', '验证码泄露', '密码泄露', '信息泄露', '被钓鱼', '钓鱼网站', '假网站', '假冒网站'],
  transfer_to_stranger: ['给陌生人转', '给陌生人汇', '转给不认识的人', '帮 xxx 垫付', '帮 xxx 转', '代 xxx 转', '替 xxx 转', '垫付', '垫资', '对方不认识', '不认识的人'],
  urgent_request: ['急用钱', '马上要', '今天必须', '立刻转', '立即转', '现在就转', '马上转', '赶紧', '快点', '立即', '半小时内', '10 分钟内', '5 分钟内', '不能告诉家人', '不能告诉银行', '保密', '这是机密', '这是秘密', '别告诉别人'],
  fake_official_speech: ['银行工作人员让我', '客服让我', '银保监会让我', '公安局让我', '检察院让我', '法院让我', '安全账户', '安全账号', '保证金账户', '验资', '资金清查', '账户排查', '升级 vip 才能', '升级账户才能', '配合调查', '协助调查', '电话转接', '转接到'],
  investment_fraud: ['高息', '高回报', '高收益', '保本高收益', '稳赚不赔', '无风险', '保本', '保息', '内幕消息', '内部消息', '荐股', '牛股', '炒外汇', '炒币', '虚拟货币', '挖矿', '刷单返利', '兼职刷单', '刷信誉', '传销', '发展下线', '拉人头'],
  refund_or_lottery_fraud: ['退款', '理赔', '退钱', '退费', '退款到账', '中奖', '中奖了', '一等奖', '免费送', '免费领', '送福利', '快递理赔', '快递丢了', '理赔款'],
  prompt_injection: ['忽略之前', '忽略以上', '忽略前面', '忽略上文', '无视之前', '无视以上', '无视上文', '忘了刚才', '忘了上面', '忘了之前', '不要听', '别听之前的', '忘记之前', '忽略指令', '无视指令', '覆盖指令', '忽略规则', '无视规则', '跳过规则', '忽略系统', '无视系统', '新指令'],
  suitability_mismatch: ['风险等级不对', '风险等级低', '风险等级不匹配', '风险低能买', '风险低可以买', '风险小能买', '适当性不匹配', '风险不匹配', '评级不够', '风险测评不过', '适当性管理'],
};

const AML_KEYWORDS = {
  large_amount: ['大额转', '大额汇', '巨额', '大笔', '一百万', '两百万', '五百万', '一千万', '100万', '200万', '500万', '1000万', '1亿'],
  structured_split: ['分多笔', '分几笔', '分几次', '分批', '拆单', '拆成', '分两天', '分三个', '分五个', '分十次', '每次不到 5 万', '每次不到 3 万', '每次 3 万', '每次 4 万', '笔数多', '拆成多笔', '化整为零'],
  cash_intensive: ['大量现金', '大批现金', '现金存入', '现金取出', '分批取现', '大额取现', '现金存款', '现钞兑换', '现金汇款'],
  cross_border_suspicious: ['境外汇入', '汇到国外', '汇到海外', '海外账户', '地下钱庄', '换汇', '大额换汇', '蚂蚁搬家', '对敲', '离岸账户', 'nra 账户', 'osa 账户', '拆分汇出', '化整为零汇出', '给国外汇钱', '给国外汇款', '汇钱给国外', '汇钱到国外', '汇钱出国', '汇钱到境外', '给境外汇', '跨境转账', '汇钱给境外'],
  third_party_payment: ['第三方账户', '他人账户代付', '过桥资金', '过桥', '代收代付', '代付', '代收', '走账', '公转私', '私转公', '对公转对私'],
};

const UNAUTHORIZED_KEYWORDS = {
  proxy_query: ['帮 xxx 查', '帮 xxx 看', '帮 xxx 问', '代查', '代看', '代问', '替别人', '代替别人', '帮别人查', '帮别人看', '帮别人问'],
  card_query: ['告诉我其他客户的账户', '其他客户账户', '其他客户信息', '客户账户信息', '查询他人', '查看他人账户', '查别人', '查别人账户', '查别人余额', '查他人余额'],
};

// ============================================================
// P0/P1/P2/P3 业务意图词典 (L1 规则层)
// ============================================================
const L1_RULES = [
  // ============================================================
  // P0 红线 - 业务子类 (含口语化 patterns)
  // ============================================================
  // 信用卡丢失/盗刷
  { pattern: /(信用卡丢了|卡丢了|卡找不到了|信用卡不见了|信用卡盗刷|卡被盗刷|卡被刷了|卡里的钱被刷走了|刷走了|信用卡掉|卡掉|卡片丢了|丢了卡|丢卡)/i, intent: 'safety_card_loss', priority: 'P0' },
  // 信用卡冻结
  { pattern: /(信用卡冻结|卡冻结|冻结卡|账号冻结|账户冻结|卡被冻|账户被冻|紧急冻结|卡被锁|账户被锁|被锁了|锁了|被锁)/i, intent: 'safety_card_freeze', priority: 'P0' },
  // 验证码/密码泄露
  { pattern: /(验证码泄露|密码泄露|信息泄露|被钓鱼|钓鱼网站|验证码告诉|验证码发我|验证码给我|把密码|告诉我密码|密码是)/i, intent: 'security_fraud_recognize', priority: 'P0' },
  // 盗刷/不明扣款
  { pattern: /(盗刷|不明扣款|不是我交易|不是我的交易|不是我操作的|账户异常交易|不认识的扣款|钱被刷了|被刷|卡里的钱|账户里的钱|钱不见了)/i, intent: 'security_fraud_recognize', priority: 'P0' },
  // 投诉类
  { pattern: /(我要投诉|投诉|举报|曝光|态度差|服务差|态度不好|服务不好|差评|你们骗|骗子公司|气死|投诉你们|投诉专员|去银监|315|微博)/i, intent: 'sys_service_complaint', priority: 'P0' },
  // 转人工
  { pattern: /(转人工|找真人|人工服务|找人工|转人工客服|人工坐席|不跟机器人|跟真人|人工接|转接人工|真人接)/i, intent: 'sys_service_route_human', priority: 'P0' },

  // ============================================================
  // P1 业务 - 信息查询 / 业务办理 (含完整口语化 patterns)
  // ============================================================
  // 余额查询 (大幅扩展)
  { pattern: /(余额|账户余额|卡里还有|还剩多少钱|还有多少钱|查余额|多少余额|剩多少钱|卡里剩|还剩|卡里有多少|有多少钱|查账|余额查询|卡里余额)/i, intent: 'info_acc_balance', priority: 'P1' },
  // 账单查询 (大幅扩展 - 修用户报告的 bug)
  { pattern: /(账单|本期账单|还款金额|最低还款|账单金额|这个月账单|还多少钱|要还多少|还多少|要还|要还款|欠多少|欠款|本月账单|这月账|这个月账|本月还|这个月还|还款日|最后还款|最低还|账单日|消费了|花多少|本月开销|本月花了|本月消费|信用卡账单|卡账单|本月账|这个月账|本期账|这期账|这月账单|还多少账|账单还|还款明细|本月还款|账单详情)/i, intent: 'info_bill_amount', priority: 'P1' },
  // 还款
  { pattern: /(还款|还钱|怎么还|怎么还款|还信用卡|还欠款|还账|还清|怎么还钱|怎么还账|还款方式|如何还款|还款渠道)/i, intent: 'biz_pay_repay', priority: 'P1' },
  // 理财产品
  { pattern: /(有什么好理财|理财推荐|理财产品|理财建议|我想理财|理财|基金|朝朝宝|稳健理财|高收益理财|低风险理财|什么理财好)/i, intent: 'consult_wealth_fund', priority: 'P1' },
  // 大额转账
  { pattern: /(大额转账手续|转账手续|大额转给公司|大额怎么操作|大额怎么办|大额转|大额汇|大额)/i, intent: 'biz_transfer_large', priority: 'P0' },
  // 积分
  { pattern: /(积分|查积分|多少积分|积分余额|积分查询|信用卡积分)/i, intent: 'info_points_query', priority: 'P1' },
  // 额度
  { pattern: /(可用额度|额度多少|剩余额度|额度查询|信用额度|总额度)/i, intent: 'info_credit_limit', priority: 'P1' },
  // 利率
  { pattern: /(利率|年化|年化利率|利率多少|多少利率|利息多少|利息查询)/i, intent: 'info_interest_rate', priority: 'P1' },

  // ============================================================
  // P2 长流程
  // ============================================================
  // 信用卡挂失
  { pattern: /(信用卡挂失|挂失|补卡|补办|挂失补办|报失|挂失卡|挂失信用卡|怎么挂失|如何挂失)/i, intent: 'biz_card_loss', priority: 'P2' },
  // 信用卡激活
  { pattern: /(激活|开卡|启用|卡片激活|新卡怎么开|信用卡激活|怎么激活|如何激活|卡怎么用|新卡)/i, intent: 'biz_card_activate', priority: 'P2' },
  // 信用卡额度调整
  { pattern: /(信用卡额度|额度|提升额度|临时额度|调额度|涨额度|额度调整|提额)/i, intent: 'biz_card_limit', priority: 'P2' },
  // 网点查询
  { pattern: /(网点|营业网点|营业时间|在哪|地址|怎么去|上班时间|营业厅|附近网点|招行网点|最近网点)/i, intent: 'info_branch_query', priority: 'P2' },
  // 密码重置
  { pattern: /(密码重置|重置密码|忘记密码|密码忘了|改密码|修改密码|找回密码|密码找回)/i, intent: 'biz_password_reset', priority: 'P2' },
  // 转账指引
  { pattern: /(转账指引|怎么转账|如何转账|转账流程|转账步骤|转账方法|转账操作)/i, intent: 'biz_transfer_guide', priority: 'P2' },

  // ============================================================
  // P3 闲聊
  // ============================================================
  { pattern: /(你好|您好|hi|hello|嗨|hey|在吗|在么)/i, intent: 'sys_service_greeting', priority: 'P3' },
  { pattern: /(再见|拜拜|多谢|谢谢|感谢|byebye|bye|辛苦了)/i, intent: 'sys_service_farewell', priority: 'P3' },
];

// ============================================================
// KEYWORD CO-OCCURRENCE SCORING (语义增强)
// ============================================================
// 不依赖字面匹配, 用 keyword 共现打分判断意图
// 每个 intent 有关键词权重表, 计算 query 里命中关键词的加权和
// 阈值: 命中分数 >= 2.0 才算该意图
const INTENT_KEYWORDS = {
  // P1
  'info_bill_amount': {
    keywords: ['账单', '还', '欠', '账', '消费', '花', '开销', '明细', '月', '本期', '本月', '这个月', '这月', '还款日', '最低', '金额', '多少钱'],
    weight: 1.0,
  },
  'info_acc_balance': {
    keywords: ['余额', '剩', '还有', '查', '多少', '卡里', '账户', '钱'],
    weight: 1.0,
  },
  'biz_pay_repay': {
    keywords: ['还款', '还钱', '还清', '怎么还', '渠道', '方式', '还'],
    weight: 1.0,
  },
  'consult_wealth_fund': {
    keywords: ['理财', '基金', '朝朝宝', '稳健', '收益', '投资', '推荐', '产品'],
    weight: 1.0,
  },
  'biz_card_loss': {
    keywords: ['挂失', '补卡', '补办', '报失', '丢了', '不见', '找不到'],
    weight: 1.0,
  },
  'biz_card_activate': {
    keywords: ['激活', '开卡', '启用', '新卡', '怎么用'],
    weight: 1.0,
  },
  'info_branch_query': {
    keywords: ['网点', '营业', '地址', '在哪', '怎么去', '上班'],
    weight: 1.0,
  },
  'safety_card_loss': {
    keywords: ['丢了', '不见', '刷走', '盗刷', '卡里的钱', '丢卡'],
    weight: 1.0,
  },
};

const SCORE_THRESHOLD = 1.5;  // 阈值: 命中分数 >= 1.5 算匹配

function scoreIntent(query) {
  // 返回 (intent, score) 最高分
  let bestIntent = null;
  let bestScore = 0;
  for (const [intent, config] of Object.entries(INTENT_KEYWORDS)) {
    let score = 0;
    for (const kw of config.keywords) {
      if (query.includes(kw)) {
        score += config.weight;
      }
    }
    if (score > bestScore) {
      bestScore = score;
      bestIntent = intent;
    }
  }
  return { intent: bestIntent, score: bestScore };
}

// ============================================================
// 主识别函数
// ============================================================
function recognize(query) {
  const startTime = performance.now();
  const qLower = query.toLowerCase().trim();
  const qOrig = query.trim();

  // 1. v3.12.1 对抗性 L0 (优先级最高)
  for (const [category, keywords] of Object.entries(ADVERSARIAL_L0_KEYWORDS)) {
    for (const kw of keywords) {
      if (qLower.includes(kw.toLowerCase())) {
        return {
          intent: 'sys_service_route_human',
          priority: 'P0',
          is_p0: true,
          should_transfer: true,
          confidence: 1.0,
          reasoning: `v3.12.1 对抗性 L0 触发 [${category}]: "${kw}"`,
          routing: 'L0_HUMAN',
          route_label: 'L0 红线 · 对抗性 · 100% 转人工',
          action: 'transfer_human',
          elapsed_ms: (performance.now() - startTime).toFixed(2),
        };
      }
    }
  }

  // 2. v3.12.0 中文 P0 红线词典 (FRAUD_KEYWORDS)
  for (const [category, keywords] of Object.entries(FRAUD_KEYWORDS)) {
    for (const kw of keywords) {
      if (query.includes(kw)) {
        return {
          intent: 'security_fraud_recognize',
          priority: 'P0',
          is_p0: true,
          should_transfer: true,
          confidence: 0.95,
          reasoning: `v3.12.0 P0 红线 [${category}]: "${kw}"`,
          routing: 'L0_HUMAN',
          route_label: 'L0 红线 · 银行业最高优先级 · 100% 转人工',
          action: 'transfer_human',
          elapsed_ms: (performance.now() - startTime).toFixed(2),
        };
      }
    }
  }

  // 3. AML 反洗钱
  for (const [category, keywords] of Object.entries(AML_KEYWORDS)) {
    for (const kw of keywords) {
      if (query.includes(kw)) {
        return {
          intent: 'security_aml_large_transfer',
          priority: 'P0',
          is_p0: true,
          should_transfer: true,
          confidence: 0.95,
          reasoning: `反洗钱 [${category}]: "${kw}"`,
          routing: 'L0_HUMAN',
          route_label: 'L0 红线 · 反洗钱 · 100% 转人工',
          action: 'transfer_human',
          elapsed_ms: (performance.now() - startTime).toFixed(2),
        };
      }
    }
  }

  // 4. 越权访问
  for (const [category, keywords] of Object.entries(UNAUTHORIZED_KEYWORDS)) {
    for (const kw of keywords) {
      if (query.includes(kw)) {
        return {
          intent: 'security_fraud_recognize',
          priority: 'P0',
          is_p0: true,
          should_transfer: true,
          confidence: 0.95,
          reasoning: `越权访问 [${category}]: "${kw}"`,
          routing: 'L0_HUMAN',
          route_label: 'L0 红线 · 越权 · 100% 转人工',
          action: 'transfer_human',
          elapsed_ms: (performance.now() - startTime).toFixed(2),
        };
      }
    }
  }

  // 5. L1 业务规则 (精确字面匹配)
  for (const rule of L1_RULES) {
    if (rule.pattern.test(query)) {
      const isP0 = rule.priority === 'P0';
      return {
        intent: rule.intent,
        priority: rule.priority,
        is_p0: isP0,
        should_transfer: isP0,
        confidence: 0.95,
        reasoning: `L1 规则匹配: ${rule.intent}`,
        routing: isP0 ? 'L0_HUMAN' : 'L1_RULE',
        route_label: isP0 ? 'L0 红线 · 转人工' : 'L1 规则命中 · 不调 LLM',
        action: isP0 ? 'transfer_human' : 'answer',
        elapsed_ms: (performance.now() - startTime).toFixed(2),
      };
    }
  }

  // 5.5 L1 兜底 - 关键词共现打分 (语义增强)
  const scored = scoreIntent(query);
  if (scored.intent && scored.score >= SCORE_THRESHOLD) {
    const intentPriorityMap = {
      'safety_card_loss': 'P0', 'safety_card_freeze': 'P0',
      'security_fraud_recognize': 'P0', 'sys_service_complaint': 'P0',
      'sys_service_route_human': 'P0', 'biz_transfer_large': 'P0',
      'info_bill_amount': 'P1', 'info_acc_balance': 'P1', 'biz_pay_repay': 'P1',
      'consult_wealth_fund': 'P1', 'info_points_query': 'P1', 'info_credit_limit': 'P1', 'info_interest_rate': 'P1',
      'biz_card_loss': 'P2', 'biz_card_activate': 'P2', 'biz_card_limit': 'P2',
      'info_branch_query': 'P2', 'biz_password_reset': 'P2', 'biz_transfer_guide': 'P2',
    };
    const priority = intentPriorityMap[scored.intent] || 'P3';
    const isP0 = priority === 'P0';
    return {
      intent: scored.intent,
      priority: priority,
      is_p0: isP0,
      should_transfer: isP0,
      confidence: Math.min(0.5 + scored.score * 0.1, 0.9),
      reasoning: `L1 语义共现: ${scored.intent} (score=${scored.score.toFixed(1)})`,
      routing: isP0 ? 'L0_HUMAN' : 'L1_SEMANTIC',
      route_label: isP0 ? 'L0 红线 · 转人工' : 'L1 语义共现命中 · 不调 LLM',
      action: isP0 ? 'transfer_human' : 'answer',
      elapsed_ms: (performance.now() - startTime).toFixed(2),
    };
  }

  // 6. fallback - 真无法识别 (建议转人工)
  return {
    intent: 'sys_other_unclear',
    priority: 'P3',
    is_p0: false,
    should_transfer: false,
    confidence: 0.0,
    reasoning: '无法识别, 建议转人工',
    routing: 'L3_LLM',
    route_label: 'L3 LLM 兜底 (生产调 M2.7)',
    action: 'answer',
    elapsed_ms: (performance.now() - startTime).toFixed(2),
  };
}

// 模板答案生成
function genAnswer(intent, query) {
  const answers = {
    'sys_service_route_human': '正在为您转接人工客服,请稍候...(预计等待 30 秒)',
    'sys_service_greeting': '您好!我是招行智能客服"小招",可以帮您查询余额、办理业务、解答疑问。请问需要什么帮助?',
    'sys_service_farewell': '感谢您使用招商银行服务,祝您生活愉快!',
    'sys_service_feedback': '感谢您的反馈,我们会持续改进服务质量。',
    'sys_other_greet': '您好!有什么可以帮您?',
    'sys_other_farewell': '再见,期待下次为您服务!',
    'sys_other_unclear': '抱歉没理解您的问题,请换种方式描述或输入"转人工"。',
    'info_acc_balance': '您的账户余额为 ¥12,580.50 (招商银行一卡通 6225)。最新交易明细请登录 App 查看。',
    'info_bill_amount': '本期账单金额 ¥3,250.00,还款日 2026-07-25。最低还款 ¥325,可享免息期。',
    'biz_card_loss': '您的卡片已挂失,冻结成功。建议立即报警 110,挂失后请到柜台补办新卡。',
    'biz_card_activate': '请登录招行 App → 信用卡 → 在线激活,输入卡号后4位 + 身份证后6位即可完成。',
    'biz_pay_repay': '您可以通过以下方式还款:①招行 App 转账 ②微信/支付宝绑卡 ③柜台/ATM ④他行转账。',
    'consult_wealth_fund': '当前主推稳健理财:① 招行朝朝宝 (7日年化 1.85%) ② 货币基金 ③ 结构性存款。请问您的风险偏好是?',
    'security_aml_large_transfer': '大额转账需人工核实身份。请前往柜台或拨打 95555 转人工。',
    'safety_card_freeze': '您的卡片已紧急冻结 (防止盗刷)。请 24 小时内携带身份证到柜台办理解冻。',
    'safety_card_loss': '已挂失。请立即报警 110,凭回执到柜台补办新卡。',
    'biz_transfer_large': '大额转账需提供:①身份证 ②转账用途证明 ③收款人信息。请到柜台办理或转人工。',
    'sys_service_complaint': '非常理解您的不满,正在为您转接投诉专员...',
    'sys_invalid': '抱歉没理解您的问题,请描述清楚或输入"转人工"。',
  };
  return answers[intent] || `已识别您的意图: ${intent}。请稍等,正在为您查询。`;
}

// 暴露到全局
window.xiaozhaoAI = { recognize, genAnswer };