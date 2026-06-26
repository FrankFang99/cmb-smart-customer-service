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
  // P0 红线 - 业务子类
  { pattern: /(信用卡丢了|卡丢了|卡找不到了|信用卡不见了|信用卡盗刷|卡被盗刷|卡被刷了|信用卡丢了)/i, intent: 'safety_card_loss', priority: 'P0' },
  { pattern: /(信用卡冻结|卡冻结|冻结卡|账号冻结|账户冻结|卡被冻|账户被冻|紧急冻结)/i, intent: 'safety_card_freeze', priority: 'P0' },
  { pattern: /(验证码泄露|密码泄露|信息泄露|被钓鱼|钓鱼网站)/i, intent: 'security_fraud_recognize', priority: 'P0' },
  { pattern: /(盗刷|不明扣款|不是我交易|不是我的交易|不是我操作的|账户异常交易|不认识的扣款)/i, intent: 'security_fraud_recognize', priority: 'P0' },
  { pattern: /(我要投诉|投诉|举报|曝光|态度差|服务差|态度不好|服务不好|差评)/i, intent: 'sys_service_complaint', priority: 'P0' },
  { pattern: /(转人工|找真人|人工服务|找人工|转人工客服|人工坐席|不跟机器人)/i, intent: 'sys_service_route_human', priority: 'P0' },

  // P1 业务
  { pattern: /(余额|账户余额|卡里还有|还剩多少钱|还有多少钱|查余额)/i, intent: 'info_acc_balance', priority: 'P1' },
  { pattern: /(账单|本期账单|还款金额|最低还款|账单金额|这个月账单)/i, intent: 'info_bill_amount', priority: 'P1' },
  { pattern: /(还款|还钱|怎么还|怎么还款|还信用卡|还欠款)/i, intent: 'biz_pay_repay', priority: 'P1' },
  { pattern: /(有什么好理财|理财推荐|理财产品|理财建议|我想理财)/i, intent: 'consult_wealth_fund', priority: 'P1' },
  { pattern: /(大额转账手续|转账手续|大额转给公司|大额怎么操作|大额怎么办)/i, intent: 'biz_transfer_large', priority: 'P0' },

  // P2 长流程
  { pattern: /(信用卡挂失|挂失|补卡|补办|挂失补办)/i, intent: 'biz_card_loss', priority: 'P2' },
  { pattern: /(激活|开卡|启用|卡片激活|新卡怎么开|信用卡激活)/i, intent: 'biz_card_activate', priority: 'P2' },
  { pattern: /(信用卡额度|额度|提升额度|临时额度)/i, intent: 'biz_card_limit', priority: 'P2' },
  { pattern: /(网点|营业网点|营业时间|在哪|地址|怎么去|上班时间|营业厅)/i, intent: 'info_branch_query', priority: 'P2' },

  // P3 闲聊
  { pattern: /(你好|您好|hi|hello|嗨)/i, intent: 'sys_service_greeting', priority: 'P3' },
  { pattern: /(再见|拜拜|多谢|谢谢|感谢)/i, intent: 'sys_service_farewell', priority: 'P3' },
];

// ============================================================
// 主识别函数
// ============================================================
function recognize(query) {
  const startTime = performance.now();
  const qLower = query.toLowerCase().trim();

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

  // 2. v3.12.0 中文 P0 红线词典
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

  // 5. L1 业务规则
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

  // 6. fallback
  return {
    intent: 'sys_other_unclear',
    priority: 'P3',
    is_p0: false,
    should_transfer: false,
    confidence: 0.0,
    reasoning: '无法识别,默认归类',
    routing: 'L3_LLM',
    route_label: 'L3 LLM 兜底',
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