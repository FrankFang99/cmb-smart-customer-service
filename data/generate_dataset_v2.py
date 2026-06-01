"""
招商银行智能客服评测数据集生成器 v2.0
基于意图分类体系 v2.0 生成真实场景评测数据

设计原则：
1. 真实口语化：模拟真实客户的表达方式
2. 多样变体：同一意图多个表达方式
3. 噪声覆盖：包含方言、错别字、口语化表达
4. 边界case：包含模糊、复杂、边界场景
"""
import json
import random
from typing import List, Dict, Any
from dataclasses import dataclass, asdict


@dataclass
class EvalSample:
    """评测样本"""
    id: str
    category: str  # 一级分类
    sub_category: str  # 二级分类
    intent: str  # 意图ID
    question: str  # 问题（口语化）
    expected_intent: str  # 期望意图
    expected_keywords: List[str]  # 期望关键词
    required_disclosure: bool  # 是否需要风险提示
    transfer_required: bool  # 是否需要转人工
    transfer_priority: str  # P0/P1/P2
    difficulty: str  # easy/medium/hard
    source: str  # manual/template/augment
    emotion: str  # neutral/angry/urgent/anxious/pleased


class DatasetGeneratorV2:
    """评测数据集生成器 v2.0"""
    
    def __init__(self):
        self.samples = []
        self.sample_counter = 0
        
        # 真实客户口语化表达模板
        self._init_templates()
    
    def _init_templates(self):
        """初始化问题模板"""
        
        # ============================================
        # INFO - 信息查询类
        # ============================================
        
        # 余额查询
        self.templates["info_acc_balance"] = [
            "我卡里还有多少钱啊",
            "帮我看看账户还有多少",
            "余额查一下",
            "最近好像没什么钱了，剩多少",
            "剩多少",
            "我还有多少",
            "余额多少",
            "账户上还有钱吗",
            "看看还剩多少",
            "我这张卡没钱了吧",
            "余额还有多少咯",
            "我卡上还有银子不",
            "有多少Money",
            "帮我查下余额",
            "余额多少啊，急用",
            "卡里还剩多钱",
            "帮我看看还有多少可以用",
            "钱还够吗",
            "还剩多少银子",
            "余额查询",
        ]
        
        # 账户明细
        self.templates["info_acc_detail"] = [
            "帮我查查最近都花了什么",
            "交易记录看一下",
            "最近有什么消费",
            "流水记录打印一下",
            "看看我的账单明细",
            "都有哪些交易",
            "收支记录",
            "最近几笔交易是什么",
            "消费记录在哪看",
            "查一下流水",
            "最近一个月花了多少",
            "显示一下交易明细",
            "我都买了什么",
            "交易历史",
            "账户变动明细",
        ]
        
        # 账单金额
        self.templates["info_bill_amount"] = [
            "这个月账单多少",
            "欠了多少钱",
            "本期账单金额",
            "该还多少",
            "账单出来了没",
            "看看本期要还多少",
            "欠款多少",
            "这个月要还信用卡多少",
            "账单多少银子",
            "我该还得数目",
            "本期账务",
            "总欠多少",
            "看看账单",
            "欠银行多少",
            "信用卡欠多少",
        ]
        
        # 还款日期
        self.templates["info_bill_date"] = [
            "还款日是几号",
            "几号之前要还",
            "截止日期是哪天",
            "最晚什么时候还",
            "还款deadline",
            "哪天是还款日",
            "最后一天是哪天",
            "还款截止时间",
            "宽限期到几号",
            "几号之前一定得还",
            "还钱截止日期",
            "还款最晚日期",
            "哪天之前要存够钱",
            "还信用卡哪天",
        ]
        
        # 最低还款
        self.templates["info_bill_min"] = [
            "最低要还多少",
            "最少还这个数对吧",
            "最低还款额多少",
            "只还最低影响信用吗",
            "最低还款划算吗",
            "按最低还就行吧",
            "最低还款额是多少",
            "只付最低额度可以吗",
            "最少多少钱",
            "最低还款政策",
        ]
        
        # 积分查询
        self.templates["info_bill_point"] = [
            "我有多少积分",
            "积分能干嘛",
            "积分怎么用",
            "积分换什么好",
            "积分过期了吗",
            "积分商城在哪",
            "现在积分多少",
            "积分能换什么礼品",
            "积分怎么兑换",
            "查一下积分",
        ]
        
        # ============================================
        # BIZ - 业务办理类
        # ============================================
        
        # 卡片挂失
        self.templates["biz_card_loss"] = [
            "我的卡丢了怎么办",
            "卡不见了要挂失",
            "卡片丢失怎么操作",
            "卡掉了能帮我挂一下吗",
            "银行卡丢了",
            "信用卡不见了",
            "要挂失我的卡",
            "卡被偷了",
            "卡找不到了",
            "卡片丢失紧急处理",
            "卡丢了急死了",
            "帮我把卡冻了",
            "卡要挂失",
            "卡片丢了怎么弄",
            "要立即挂失",
        ]
        
        # 卡片激活
        self.templates["biz_card_activate"] = [
            "新卡怎么激活",
            "卡拿到了怎么开",
            "激活信用卡",
            "怎么启用卡片",
            "收到卡了怎么用",
            "卡片开卡流程",
            "新收到的卡怎么开通",
            "卡激活不了",
            "激活码是什么",
            "怎么开卡",
            "帮我激活一下",
            "卡片启用了没有",
        ]
        
        # 密码重置
        self.templates["biz_pwd_reset"] = [
            "密码忘了怎么办",
            "忘记密码了",
            "密码丢失",
            "密码不记得了",
            "忘了密码怎么弄",
            "密码给忘了",
            "记不住密码",
            "密码忘记了",
            "怎么重置密码",
            "帮我改密码但是忘了",
            "密码找不到了",
            "设置新密码",
        ]
        
        # 密码修改
        self.templates["biz_pwd_change"] = [
            "我想改密码",
            "换个密码",
            "修改密码",
            "密码太老了换一个",
            "更新密码",
            "改一下密码",
            "换一个新密码",
            "密码要更新",
        ]
        
        # 行内转账
        self.templates["biz_tran_internal"] = [
            "转1000给我老婆",
            "给我哥转点钱",
            "招行卡之间转账",
            "同行转账",
            "转到招行卡",
            "给朋友转两万",
            "转账到同城账户",
            "招行互转",
            "账户互转",
            "行内汇款",
            "给家人转钱",
            "转账给我同事",
            "帮转一下账",
        ]
        
        # 跨行转账
        self.templates["biz_tran_external"] = [
            "转钱到工行",
            "跨行汇款手续费",
            "转建行可以吗",
            "给他行转账",
            "别的银行转账",
            "跨行转要多久",
            "农行卡转账",
            "中国银行转账",
            "跨行汇款怎么弄",
            "给他行账户转账",
            "我要转3万到别的银行",
            "跨行转账多久到账",
        ]
        
        # 撤销转账
        self.templates["biz_tran_reverse"] = [
            "转错了能撤回吗",
            "钱转错人了怎么办",
            "撤销这笔转账",
            "转错了怎么追回",
            "可以撤销吗",
            "转账能撤回吗",
            "转错账户了",
            "后悔了怎么取消",
            "我要撤销刚才那笔",
            "转账能取消吗",
            "转错了人怎么弄",
        ]
        
        # 还款操作
        self.templates["biz_pay_repay"] = [
            "帮我还款",
            "还信用卡的钱",
            "转账还款",
            "怎么还钱",
            "还款操作",
            "我要还款",
            "把钱还到信用卡",
            "怎么把欠款还上",
            "还款怎么弄",
            "帮忙还一下",
        ]
        
        # 自动还款设置
        self.templates["biz_pay_autopay"] = [
            "设置自动还款",
            "每月自动扣款",
            "自动还信用卡",
            "怎么开自动还款",
            "到期自动扣款",
            "绑定自动还款",
            "自动扣款设置",
            "怎样开通自动还款",
        ]
        
        # 逾期处理
        self.templates["biz_pay_overdue"] = [
            "已经逾期了怎么办",
            "晚还了几天会怎样",
            "逾期一天有事吗",
            "已经逾期3天了",
            "忘记还款逾期了",
            "逾期会有什么影响",
            "滞纳金多少",
            "已经逾期怎么补救",
            "逾期记录能消除吗",
        ]
        
        # 分期办理
        self.templates["biz_installment"] = [
            "账单能分期吗",
            "我想分12期",
            "分期手续费多少",
            "消费分期怎么办",
            "怎么办分期",
            "分期付款怎么弄",
            "能不能分几个月",
            "我想分期还",
            "大件分期",
            "分3期可以吗",
        ]
        
        # ============================================
        # CONSULT - 咨询投诉类
        # ============================================
        
        # 理财咨询 [需要风险提示]
        self.templates["cons_prod_wealth"] = [
            "理财产品安全吗",
            "会亏本吗",
            "理财收益多少",
            "有什么推荐的理财",
            "理财风险大不大",
            "保本理财有吗",
            "年化收益多少",
            "理财怎么选",
            "理财比存款好吗",
            "理财可靠吗",
            "稳健型理财推荐",
            "收益和风险怎么平衡",
            "买理财靠谱吗",
        ]
        
        # 贷款咨询 [需要风险提示]
        self.templates["cons_prod_loan"] = [
            "贷款利率多少",
            "信用贷利息怎么算",
            "贷款需要什么条件",
            "能贷多少",
            "贷款审批要多久",
            "月供多少",
            "还款方式怎么选",
            "抵押贷信用贷哪个好",
            "贷款有什么要求",
            "贷款额度怎么定",
            "利率优惠吗",
        ]
        
        # 信用卡咨询 [需要风险提示]
        self.templates["cons_prod_credit"] = [
            "额度多少",
            "怎么提额",
            "年费多少",
            "有什么权益",
            "哪个卡种好",
            "怎么办信用卡",
            "申请条件是什么",
            "金卡和普卡区别",
            "visa还是mastercard",
            "有什么优惠",
            "积分怎么算",
            "怎么注销",
        ]
        
        # 产品对比 [需要风险提示]
        self.templates["cons_prod_compare"] = [
            "定期和理财哪个好",
            "信用贷和抵押贷比较",
            "招行和建行贷款哪个划算",
            "哪个产品收益高",
            "理财产品对比",
            "存款还是理财",
            "消费贷信用贷区别",
            "不同信用卡对比",
            "哪个更划算",
        ]
        
        # 转账手续费
        self.templates["cons_fee_tran"] = [
            "跨行转账手续费多少",
            "转账要收多少手续费",
            "汇款收费吗",
            "跨行汇款费用",
            "手续费怎么算",
            "行内转账收费吗",
            "免手续费吗",
            "转账费率",
        ]
        
        # 取现手续费
        self.templates["cons_fee_withdrw"] = [
            "取现手续费多少",
            "atm取现收多少",
            "信用卡取现有费用吗",
            "取现利息怎么算",
            "每天取现限额",
            "取现收手续费吗",
        ]
        
        # 分期手续费
        self.templates["cons_fee_install"] = [
            "分期手续费多少",
            "分12期利率多少",
            "分期的实际年化",
            "分期划算吗",
            "手续费怎么收",
            "分期有利息吗",
        ]
        
        # 服务投诉 [P0]
        self.templates["cons_comp_service"] = [
            "你们服务态度太差了",
            "客服怎么这个态度",
            "要投诉",
            "我要举报你们",
            "服务不满意",
            "太敷衍了",
            "等了半小时没人理",
            "效率太低了",
            "一点都不专业",
            "客服爱答不理",
            "太气人了",
            "我要投诉你们",
            "给你们差评",
        ]
        
        # 延误投诉 [P0]
        self.templates["cons_comp_delay"] = [
            "等了太久了",
            "处理太慢",
            "效率太低",
            "一个简单问题搞这么久",
            "催了好几遍没解决",
            "等了半小时还没好",
            "进度太慢了",
            "什么时候能处理完",
            "等不及了",
        ]
        
        # 错误投诉 [P0]
        self.templates["cons_comp_error"] = [
            "你们搞错了",
            "信息对不上",
            "搞错了吧",
            "数据错了",
            "账户余额不对",
            "金额有问题",
            "账单算错了",
            "记录有误",
        ]
        
        # 拒绝服务投诉 [P0]
        self.templates["cons_comp_refuse"] = [
            "为什么不给我办",
            "不给我处理",
            "推来推去",
            "踢皮球",
            "不给解决",
            "拒绝服务",
            "说办不了",
            "来回推诿",
        ]
        
        # 资金损失 [P0]
        self.templates["cons_urg_loss"] = [
            "我的钱没了！",
            "账户的钱不见了",
            "钱被转走了",
            "资金异常",
            "钱突然没了急死了",
            "钱丢了怎么办",
            "账户钱少了很多",
            "大额资金消失",
        ]
        
        # 账户锁定 [P0]
        self.templates["cons_urg_lock"] = [
            "账户被锁了",
            "登录不了了",
            "密码连续输错",
            "卡被冻了不能用",
            "账户异常锁定",
            "为什么登录不了",
            "账户被停用了",
            "无法使用服务",
        ]
        
        # 强烈要求人工 [P0]
        self.templates["cons_urg_human"] = [
            "我要转人工",
            "帮我转客服",
            "人工服务",
            "不要AI",
            "不要机器人",
            "找真人帮我处理",
            "受不了机器了",
            "必须转人工",
            "赶紧接人工",
            "接人工服务",
            "我要跟人说",
        ]
        
        # ============================================
        # SECURITY - 安全风控类 [全部P0]
        # ============================================
        
        # 盗刷举报
        self.templates["sec_stolen_card"] = [
            "我的卡一直在身上怎么有消费！",
            "被人盗刷了！怎么办急死了！",
            "卡没丢但钱少了",
            "境外消费我没出过国",
            "消费通知不是我花的",
            "卡在身上钱没了",
            "突然有不明消费",
            "卡没离身但有扣款",
            "被盗刷了！",
            "信用卡在国外被刷了",
            "不是我刷的卡",
            "有消费我没做过",
        ]
        
        # 信息泄露
        self.templates["sec_stolen_info"] = [
            "有人知道我信息了",
            "个人信息泄露",
            "接到诈骗电话知道我的卡号",
            "账户信息被窃取",
            "隐私信息外泄",
            "我的资料被人用了",
            "信息被泄露了",
        ]
        
        # 诈骗举报
        self.templates["sec_fraud_report"] = [
            "我被骗了！",
            "遇到诈骗了怎么办",
            "转账给骗子了",
            "被假冒客服骗了",
            "网络诈骗",
            "电话诈骗",
            "钓鱼网站骗了我",
            "我举报诈骗",
        ]
        
        # 可疑交易
        self.templates["sec_fraud_suspect"] = [
            "有笔交易很奇怪",
            "可疑交易怎么上报",
            "不是我的交易",
            "发现异常交易",
            "陌生地点消费",
            "异常登录",
            "可疑活动举报",
        ]
        
        # 钓鱼链接
        self.templates["sec_fraud_phishing"] = [
            "收到钓鱼短信",
            "假银行链接",
            "假冒招行网站",
            "钓鱼邮件",
            "诈骗链接",
            "假的95555短信",
            "仿冒银行",
        ]
        
        # 账户异常冻结
        self.templates["sec_freeze_unexpected"] = [
            "我的卡突然用不了",
            "账户被冻结了？",
            "为什么突然不能用",
            "卡冻了",
            "账户异常",
            "卡被停了",
            "无法正常使用",
        ]
        
        # 申请冻结
        self.templates["sec_freeze_request"] = [
            "帮我冻结账户",
            "先把我卡冻了",
            "申请账户保护",
            "我要冻结",
            "先锁住账户",
            "安全冻结",
            "紧急冻结",
        ]
        
        # ============================================
        # SALES - 营销推广类
        # ============================================
        
        # 理财推荐 [需要风险提示]
        self.templates["sales_wealth_prod"] = [
            "有什么好的理财产品推荐",
            "推荐个稳健理财",
            "想买个理财",
            "闲钱理财",
            "短期理财推荐",
            "保本理财推荐",
            "年化高一点的理财",
        ]
        
        # 贷款推荐 [需要风险提示]
        self.templates["sales_loan_prod"] = [
            "有什么贷款推荐",
            "信用贷产品",
            "贷款产品有哪些",
            "个人贷款推荐",
            "消费贷款",
            "经营贷款",
        ]
        
        # 信用卡推荐 [需要风险提示]
        self.templates["sales_credit_prod"] = [
            "推荐张信用卡",
            "哪个信用卡好",
            "想办个卡",
            "申请信用卡",
            "信用卡推荐",
            "young卡怎么样",
        ]
        
        # 优惠活动
        self.templates["sales_promo_discount"] = [
            "最近有什么优惠",
            "打折活动",
            "满减优惠",
            "有优惠券吗",
            "周三五折去哪了",
            "周三美食半价",
            "优惠活动",
        ]
        
        # 积分活动
        self.templates["sales_credit_point"] = [
            "积分能换什么",
            "积分兑换礼品",
            "积分抵现",
            "积分抽奖",
            "积分有什么活动",
            "积分怎么用最划算",
        ]
        
        # ============================================
        # SYSTEM - 系统交互类
        # ============================================
        
        # 问候
        self.templates["sys_greeting"] = [
            "你好",
            "您好",
            "hi",
            "hello",
            "在吗",
            "在不在",
            "你好啊",
            "早上好",
        ]
        
        # 感谢
        self.templates["sys_thanks"] = [
            "谢谢",
            "感谢",
            "多谢",
            "谢啦",
            "谢谢客服",
            "辛苦了",
            "非常感谢",
        ]
        
        # 告别
        self.templates["sys_bye"] = [
            "再见",
            "拜拜",
            "886",
            "那先这样",
            "好的我知道了",
            "拜",
            "下次见",
        ]
        
        # 无效输入
        self.templates["sys_invalid"] = [
            "嗯嗯",
            "哦",
            "啊",
            "呃",
            "...",
            "。",
            " ",
            "asdf",
        ]
        
        # 无关话题
        self.templates["sys_offtopic"] = [
            "今天天气怎么样",
            "股市行情",
            "新闻",
            "娱乐八卦",
            "跟我聊聊天",
            "讲个笑话",
        ]
    
    # 模板字典（初始化）
    templates: Dict[str, List[str]] = {
        # INFO
        "info_acc_balance": [],
        "info_acc_detail": [],
        "info_acc_status": [],
        "info_acc_info": [],
        "info_bill_amount": [],
        "info_bill_date": [],
        "info_bill_min": [],
        "info_bill_point": [],
        "info_tran_record": [],
        "info_tran_status": [],
        "info_prod_wealth": [],
        "info_prod_loan": [],
        "info_prod_credit": [],
        "info_prog_application": [],
        "info_prog_transfer": [],
        "info_prog_other": [],
        "info_branch": [],
        "info_phone": [],
        "info_hour": [],
        "info_other": [],
        
        # BIZ
        "biz_tran_internal": [],
        "biz_tran_external": [],
        "biz_tran_remit": [],
        "biz_tran_reverse": [],
        "biz_tran_limit": [],
        "biz_card_loss": [],
        "biz_card_activate": [],
        "biz_card_reissue": [],
        "biz_card_damage": [],
        "biz_card_eject": [],
        "biz_card_cancel": [],
        "biz_pwd_reset": [],
        "biz_pwd_change": [],
        "biz_pwd_set": [],
        "biz_pay_repay": [],
        "biz_pay_autopay": [],
        "biz_pay_overdue": [],
        "biz_installment": [],
        "biz_statement": [],
        "biz_other": [],
        
        # CONSULT
        "cons_prod_wealth": [],
        "cons_prod_loan": [],
        "cons_prod_credit": [],
        "cons_prod_deposit": [],
        "cons_prod_compare": [],
        "cons_fee_tran": [],
        "cons_fee_withdrw": [],
        "cons_fee_install": [],
        "cons_fee_other": [],
        "cons_rule_refund": [],
        "cons_rule_cancel": [],
        "cons_rule_overdue": [],
        "cons_rule_other": [],
        "cons_comp_service": [],
        "cons_comp_delay": [],
        "cons_comp_error": [],
        "cons_comp_refuse": [],
        "cons_comp_other": [],
        "cons_sugg_improve": [],
        "cons_sugg_new": [],
        "cons_urg_loss": [],
        "cons_urg_lock": [],
        "cons_urg_card": [],
        "cons_urg_human": [],
        
        # SALES
        "sales_wealth_prod": [],
        "sales_wealth_return": [],
        "sales_wealth_risk": [],
        "sales_loan_prod": [],
        "sales_loan_rate": [],
        "sales_loan_cond": [],
        "sales_credit_prod": [],
        "sales_credit_point": [],
        "sales_credit_fee": [],
        "sales_promo_discount": [],
        "sales_promo_reward": [],
        "sales_promo_other": [],
        
        # SECURITY
        "sec_fraud_report": [],
        "sec_fraud_suspect": [],
        "sec_fraud_phishing": [],
        "sec_fraud_scam": [],
        "sec_stolen_card": [],
        "sec_stolen_info": [],
        "sec_freeze_unexpected": [],
        "sec_freeze_request": [],
        "sec_freeze_legal": [],
        "sec_virus": [],
        "sec_hack": [],
        "sec_other": [],
        
        # SYSTEM
        "sys_greeting": [],
        "sys_bye": [],
        "sys_intro": [],
        "sys_thanks": [],
        "sys_feedback": [],
        "sys_invalid": [],
        "sys_gibberish": [],
        "sys_offtopic": [],
        "sys_confirm": [],
        "sys_repeat": [],
        "sys_other": [],
    }
    
    def _init_templates(self):
        """初始化所有模板"""
        self.templates = {}
        
        # INFO类 - 信息查询
        self.templates["info_acc_balance"] = [
            "我卡里还有多少钱啊", "帮我看看账户还有多少", "余额查一下",
            "最近好像没什么钱了，剩多少", "剩多少", "我还有多少",
            "余额多少", "账户上还有钱吗", "看看还剩多少", "我这张卡没钱了吧",
            "余额还有多少咯", "我卡上还有银子不", "有多少Money", "帮我查下余额",
            "余额多少啊，急用", "卡里还剩多钱", "帮我看看还有多少可以用",
            "钱还够吗", "还剩多少银子", "余额查询",
        ]
        
        self.templates["info_acc_detail"] = [
            "帮我查查最近都花了什么", "交易记录看一下", "最近有什么消费",
            "流水记录打印一下", "看看我的账单明细", "都有哪些交易", "收支记录",
            "最近几笔交易是什么", "消费记录在哪看", "查一下流水",
            "最近一个月花了多少", "显示一下交易明细", "我都买了什么",
        ]
        
        self.templates["info_bill_amount"] = [
            "这个月账单多少", "欠了多少钱", "本期账单金额", "该还多少",
            "账单出来了没", "看看本期要还多少", "欠款多少", "这个月要还信用卡多少",
            "账单多少银子", "我该还得数目", "本期账务", "总欠多少", "看看账单",
        ]
        
        self.templates["info_bill_date"] = [
            "还款日是几号", "几号之前要还", "截止日期是哪天", "最晚什么时候还",
            "还款deadline", "哪天是还款日", "最后一天是哪天", "还款截止时间",
            "宽限期到几号", "几号之前一定得还", "还钱截止日期", "还款最晚日期",
        ]
        
        self.templates["info_bill_min"] = [
            "最低要还多少", "最少还这个数对吧", "最低还款额多少",
            "只还最低影响信用吗", "最低还款划算吗", "按最低还就行吧",
        ]
        
        self.templates["info_bill_point"] = [
            "我有多少积分", "积分能干嘛", "积分怎么用", "积分换什么好",
            "积分过期了吗", "积分商城在哪", "现在积分多少", "积分能换什么礼品",
        ]
        
        self.templates["info_tran_record"] = [
            "最近交易记录", "查看交易明细", "近期消费清单", "账户流水",
        ]
        
        self.templates["info_tran_status"] = [
            "转账到账了吗", "汇款到没", "对方收到没", "转账成功没",
        ]
        
        self.templates["info_branch"] = [
            "附近网点在哪", "最近的招行", "支行地址", "网点查询",
            "营业厅在哪", "你们营业部地址",
        ]
        
        self.templates["info_phone"] = [
            "网点电话多少", "支行电话", "客服热线", "联系电话",
        ]
        
        self.templates["info_hour"] = [
            "几点开门", "营业时间", "几点下班", "网点什么时候开门",
        ]
        
        # BIZ类 - 业务办理
        self.templates["biz_card_loss"] = [
            "我的卡丢了怎么办", "卡不见了要挂失", "卡片丢失怎么操作",
            "卡掉了能帮我挂一下吗", "银行卡丢了", "信用卡不见了", "要挂失我的卡",
            "卡被偷了", "卡找不到了", "卡片丢失紧急处理", "卡丢了急死了",
            "帮我把卡冻了", "卡要挂失", "卡片丢了怎么弄", "要立即挂失",
        ]
        
        self.templates["biz_card_activate"] = [
            "新卡怎么激活", "卡拿到了怎么开", "激活信用卡", "怎么启用卡片",
            "收到卡了怎么用", "卡片开卡流程", "新收到的卡怎么开通", "卡激活不了",
            "激活码是什么", "怎么开卡", "帮我激活一下", "卡片启用了没有",
        ]
        
        self.templates["biz_card_reissue"] = [
            "补办新卡", "卡坏了换一张", "补发卡片", "重新办卡", "新卡补办",
        ]
        
        self.templates["biz_card_eject"] = [
            "卡被ATM吞了", "机器吃卡了", "取不出来", "卡被吞",
        ]
        
        self.templates["biz_pwd_reset"] = [
            "密码忘了怎么办", "忘记密码了", "密码丢失", "密码不记得了",
            "忘了密码怎么弄", "密码给忘了", "记不住密码", "密码忘记了",
            "怎么重置密码", "帮我改密码但是忘了", "密码找不到了", "设置新密码",
        ]
        
        self.templates["biz_pwd_change"] = [
            "我想改密码", "换个密码", "修改密码", "密码太老了换一个",
            "更新密码", "改一下密码", "换一个新密码", "密码要更新",
        ]
        
        self.templates["biz_tran_internal"] = [
            "转1000给我老婆", "给我哥转点钱", "招行卡之间转账", "同行转账",
            "转到招行卡", "给朋友转两万", "转账到同城账户", "招行互转",
            "账户互转", "行内汇款", "给家人转钱", "转账给我同事", "帮转一下账",
        ]
        
        self.templates["biz_tran_external"] = [
            "转钱到工行", "跨行汇款手续费", "转建行可以吗", "给他行转账",
            "别的银行转账", "跨行转要多久", "农行卡转账", "中国银行转账",
            "跨行汇款怎么弄", "给他行账户转账", "我要转3万到别的银行",
            "跨行转账多久到账",
        ]
        
        self.templates["biz_tran_reverse"] = [
            "转错了能撤回吗", "钱转错人了怎么办", "撤销这笔转账",
            "转错了怎么追回", "可以撤销吗", "转账能撤回吗", "转错账户了",
            "后悔了怎么取消", "我要撤销刚才那笔", "转账能取消吗", "转错了人怎么弄",
        ]
        
        self.templates["biz_pay_repay"] = [
            "帮我还款", "还信用卡的钱", "转账还款", "怎么还钱",
            "还款操作", "我要还款", "把钱还到信用卡", "怎么把欠款还上",
        ]
        
        self.templates["biz_pay_autopay"] = [
            "设置自动还款", "每月自动扣款", "自动还信用卡", "怎么开自动还款",
            "到期自动扣款", "绑定自动还款", "自动扣款设置", "怎样开通自动还款",
        ]
        
        self.templates["biz_pay_overdue"] = [
            "已经逾期了怎么办", "晚还了几天会怎样", "逾期一天有事吗",
            "已经逾期3天了", "忘记还款逾期了", "逾期会有什么影响",
            "滞纳金多少", "已经逾期怎么补救",
        ]
        
        self.templates["biz_installment"] = [
            "账单能分期吗", "我想分12期", "分期手续费多少", "消费分期怎么办",
            "怎么办分期", "分期付款怎么弄", "能不能分几个月", "我想分期还",
        ]
        
        # CONSULT类 - 咨询投诉
        self.templates["cons_prod_wealth"] = [
            "理财产品安全吗", "会亏本吗", "理财收益多少", "有什么推荐的理财",
            "理财风险大不大", "保本理财有吗", "年化收益多少", "理财怎么选",
            "理财比存款好吗", "理财可靠吗", "稳健型理财推荐",
        ]
        
        self.templates["cons_prod_loan"] = [
            "贷款利率多少", "信用贷利息怎么算", "贷款需要什么条件", "能贷多少",
            "贷款审批要多久", "月供多少", "还款方式怎么选", "抵押贷信用贷哪个好",
        ]
        
        self.templates["cons_prod_credit"] = [
            "额度多少", "怎么提额", "年费多少", "有什么权益", "哪个卡种好",
            "怎么办信用卡", "申请条件是什么", "金卡和普卡区别",
        ]
        
        self.templates["cons_prod_compare"] = [
            "定期和理财哪个好", "信用贷和抵押贷比较", "招行和建行贷款哪个划算",
            "哪个产品收益高", "理财产品对比", "存款还是理财",
        ]
        
        self.templates["cons_fee_tran"] = [
            "跨行转账手续费多少", "转账要收多少手续费", "汇款收费吗",
            "跨行汇款费用", "手续费怎么算", "行内转账收费吗", "免手续费吗",
        ]
        
        self.templates["cons_fee_withdrw"] = [
            "取现手续费多少", "atm取现收多少", "信用卡取现有费用吗",
            "取现利息怎么算", "每天取现限额", "取现收手续费吗",
        ]
        
        self.templates["cons_fee_install"] = [
            "分期手续费多少", "分12期利率多少", "分期的实际年化", "分期划算吗",
        ]
        
        self.templates["cons_comp_service"] = [
            "你们服务态度太差了", "客服怎么这个态度", "要投诉", "我要举报你们",
            "服务不满意", "太敷衍了", "等了半小时没人理", "效率太低了",
            "一点都不专业", "客服爱答不理", "太气人了", "我要投诉你们",
        ]
        
        self.templates["cons_comp_delay"] = [
            "等了太久了", "处理太慢", "效率太低", "一个简单问题搞这么久",
            "催了好几遍没解决", "等了半小时还没好", "进度太慢了",
        ]
        
        self.templates["cons_comp_error"] = [
            "你们搞错了", "信息对不上", "搞错了吧", "数据错了",
            "账户余额不对", "金额有问题", "账单算错了",
        ]
        
        self.templates["cons_comp_refuse"] = [
            "为什么不给我办", "不给我处理", "推来推去", "踢皮球",
            "不给解决", "拒绝服务", "说办不了", "来回推诿",
        ]
        
        self.templates["cons_urg_loss"] = [
            "我的钱没了！", "账户的钱不见了", "钱被转走了", "资金异常",
            "钱突然没了急死了", "钱丢了怎么办", "账户钱少了很多",
        ]
        
        self.templates["cons_urg_lock"] = [
            "账户被锁了", "登录不了了", "密码连续输错", "卡被冻了不能用",
            "账户异常锁定", "为什么登录不了", "账户被停用了",
        ]
        
        self.templates["cons_urg_human"] = [
            "我要转人工", "帮我转客服", "人工服务", "不要AI", "不要机器人",
            "找真人帮我处理", "受不了机器了", "必须转人工", "赶紧接人工",
            "接人工服务", "我要跟人说",
        ]
        
        # SECURITY类 - 安全风控 [全部P0]
        self.templates["sec_stolen_card"] = [
            "我的卡一直在身上怎么有消费！", "被人盗刷了！怎么办急死了！",
            "卡没丢但钱少了", "境外消费我没出过国", "消费通知不是我花的",
            "卡在身上钱没了", "突然有不明消费", "卡没离身但有扣款",
            "被盗刷了！", "信用卡在国外被刷了", "不是我刷的卡", "有消费我没做过",
        ]
        
        self.templates["sec_stolen_info"] = [
            "有人知道我信息了", "个人信息泄露", "接到诈骗电话知道我的卡号",
            "账户信息被窃取", "隐私信息外泄", "我的资料被人用了",
        ]
        
        self.templates["sec_fraud_report"] = [
            "我被骗了！", "遇到诈骗了怎么办", "转账给骗子了",
            "被假冒客服骗了", "网络诈骗", "电话诈骗", "钓鱼网站骗了我",
        ]
        
        self.templates["sec_fraud_suspect"] = [
            "有笔交易很奇怪", "可疑交易怎么上报", "不是我的交易",
            "发现异常交易", "陌生地点消费", "异常登录",
        ]
        
        self.templates["sec_fraud_phishing"] = [
            "收到钓鱼短信", "假银行链接", "假冒招行网站", "钓鱼邮件",
            "诈骗链接", "假的95555短信",
        ]
        
        self.templates["sec_freeze_unexpected"] = [
            "我的卡突然用不了", "账户被冻结了？", "为什么突然不能用",
            "卡冻了", "账户异常", "卡被停了",
        ]
        
        self.templates["sec_freeze_request"] = [
            "帮我冻结账户", "先把我卡冻了", "申请账户保护", "我要冻结",
            "先锁住账户", "紧急冻结",
        ]
        
        # SALES类 - 营销推广
        self.templates["sales_wealth_prod"] = [
            "有什么好的理财产品推荐", "推荐个稳健理财", "想买个理财",
            "闲钱理财", "短期理财推荐", "保本理财推荐",
        ]
        
        self.templates["sales_loan_prod"] = [
            "有什么贷款推荐", "信用贷产品", "贷款产品有哪些", "个人贷款推荐",
        ]
        
        self.templates["sales_credit_prod"] = [
            "推荐张信用卡", "哪个信用卡好", "想办个卡", "申请信用卡",
            "信用卡推荐", "young卡怎么样",
        ]
        
        self.templates["sales_promo_discount"] = [
            "最近有什么优惠", "打折活动", "满减优惠", "有优惠券吗",
            "周三五折去哪了", "优惠活动",
        ]
        
        self.templates["sales_credit_point"] = [
            "积分能换什么", "积分兑换礼品", "积分抵现", "积分抽奖",
            "积分有什么活动", "积分怎么用最划算",
        ]
        
        # SYSTEM类 - 系统交互
        self.templates["sys_greeting"] = [
            "你好", "您好", "hi", "hello", "在吗", "在不在", "你好啊", "早上好",
        ]
        
        self.templates["sys_thanks"] = [
            "谢谢", "感谢", "多谢", "谢啦", "谢谢客服", "辛苦了", "非常感谢",
        ]
        
        self.templates["sys_bye"] = [
            "再见", "拜拜", "886", "那先这样", "好的我知道了", "拜", "下次见",
        ]
        
        self.templates["sys_invalid"] = [
            "嗯嗯", "哦", "啊", "呃", "...", "。", "asdf", "嘿嘿嘿",
        ]
        
        self.templates["sys_offtopic"] = [
            "今天天气怎么样", "股市行情", "新闻", "娱乐八卦", "跟我聊聊天",
        ]
    
    def generate_sample(self, intent: str, category: str, sub_category: str = "") -> EvalSample:
        """生成单个样本"""
        self.sample_counter += 1
        questions = self.templates.get(intent, [])
        
        if not questions:
            return None
        
        question = random.choice(questions)
        
        # 判断是否需要风险提示
        risk_intents = [
            "cons_prod_wealth", "cons_prod_loan", "cons_prod_credit",
            "cons_prod_deposit", "sales_wealth_prod", "sales_loan_prod",
            "sales_credit_prod", "biz_tran_internal", "biz_tran_external",
        ]
        required_disclosure = intent in risk_intents
        
        # 判断是否需要转人工
        p0_intents = [
            "cons_comp_service", "cons_comp_delay", "cons_comp_error", "cons_comp_refuse",
            "cons_urg_loss", "cons_urg_lock", "cons_urg_card", "cons_urg_human",
            "sec_fraud_report", "sec_fraud_suspect", "sec_fraud_phishing", "sec_fraud_scam",
            "sec_stolen_card", "sec_stolen_info",
            "sec_freeze_unexpected", "sec_freeze_request", "sec_freeze_legal",
        ]
        transfer_required = intent in p0_intents
        transfer_priority = "P0" if transfer_required else None
        
        # 判断情绪
        emotion = "neutral"
        if intent in ["cons_comp_service", "cons_comp_delay", "cons_urg_loss", "sec_stolen_card"]:
            emotion = random.choice(["angry", "urgent", "anxious"])
        
        return EvalSample(
            id=f"EVAL_{self.sample_counter:04d}",
            category=category,
            sub_category=sub_category or intent,
            intent=intent,
            question=question,
            expected_intent=intent,
            expected_keywords=self._get_keywords(intent),
            required_disclosure=required_disclosure,
            transfer_required=transfer_required,
            transfer_priority=transfer_priority,
            difficulty=random.choice(["easy", "medium", "hard"]),
            source="template",
            emotion=emotion,
        )
    
    def _get_keywords(self, intent: str) -> List[str]:
        """获取意图对应的关键词"""
        keywords_map = {
            # INFO类
            "info_acc_balance": ["余额", "查询", "手机银行", "APP", "账户"],
            "info_acc_detail": ["交易", "明细", "流水", "记录"],
            "info_bill_amount": ["账单", "还款", "信用卡", "掌上生活"],
            "info_bill_date": ["还款日", "账单日", "截止", "日期"],
            "info_bill_min": ["最低还款", "全额还款", "利息"],
            "info_bill_point": ["积分", "查询", "掌上生活", "兑换"],
            "info_tran_record": ["交易", "明细", "流水", "查询"],
            "info_tran_status": ["转账", "到账", "状态"],
            "info_branch": ["网点", "查询", "附近", "地址"],
            "info_phone": ["网点电话", "客服热线", "95555"],
            "info_hour": ["营业时间", "网点", "工作日"],
            
            # BIZ类
            "biz_card_loss": ["挂失", "手机银行", "冻结", "手续费"],
            "biz_card_activate": ["激活", "开卡", "身份证", "密码"],
            "biz_card_reissue": ["补卡", "网点", "身份证", "新卡"],
            "biz_card_eject": ["吞卡", "网点", "身份证", "领取"],
            "biz_pwd_reset": ["忘记密码", "重置", "验证身份"],
            "biz_pwd_change": ["修改密码", "安全中心"],
            "biz_tran_internal": ["转账", "收款人", "招行", "确认"],
            "biz_tran_external": ["跨行", "转账", "手续费", "开户银行"],
            "biz_tran_reverse": ["转账", "撤回", "报警", "核实"],
            "biz_pay_repay": ["还款", "信用卡", "手机银行"],
            "biz_pay_autopay": ["自动还款", "设置", "绑定"],
            "biz_pay_overdue": ["逾期", "滞纳金", "利息", "还款"],
            "biz_installment": ["分期", "手续费", "期数", "账单"],
            
            # CONSULT类
            "cons_prod_wealth": ["理财", "风险", "投资", "收益"],
            "cons_prod_loan": ["贷款", "利率", "额度", "还款能力"],
            "cons_prod_credit": ["信用卡", "申请", "年满", "收入"],
            "cons_prod_compare": ["产品", "风险", "理财经理", "建议"],
            "cons_fee_tran": ["转账", "手续费", "免费", "跨行"],
            "cons_fee_withdrw": ["取现", "日利率", "手续费", "利息"],
            "cons_fee_install": ["分期", "手续费", "费率", "期数"],
            "cons_comp_service": ["抱歉", "不便", "问题", "处理"],
            "cons_comp_delay": ["抱歉", "等待", "处理", "问题"],
            "cons_comp_error": ["抱歉", "不便", "核实", "处理"],
            "cons_comp_refuse": ["了解", "具体", "解决", "方案"],
            "cons_urg_loss": ["95555", "冻结", "报警", "账户"],
            "cons_urg_lock": ["95555", "核实", "身份", "解锁"],
            "cons_urg_human": ["转接", "人工", "客服", "请稍候"],
            
            # SECURITY类 [P0]
            "sec_stolen_card": ["95555", "冻结", "报警", "交易", "卡片"],
            "sec_stolen_info": ["95555", "账户", "安全", "保护"],
            "sec_fraud_report": ["95555", "报警", "冻结", "证据", "转账"],
            "sec_fraud_suspect": ["可疑", "交易", "调查", "95555", "处理"],
            "sec_fraud_phishing": ["钓鱼", "链接", "密码", "95555"],
            "sec_freeze_unexpected": ["95555", "核实", "身份", "账户", "异常"],
            "sec_freeze_request": ["95555", "冻结", "账户", "安全"],
            
            # SALES类
            "sales_wealth_prod": ["理财", "风险", "网点", "产品", "稳健"],
            "sales_loan_prod": ["贷款", "风险", "30万", "在线申请"],
            "sales_credit_prod": ["信用卡", "卡面", "YOUNG卡", "白金卡"],
            "sales_promo_discount": ["优惠", "活动", "周三", "五折", "掌上生活"],
            "sales_credit_point": ["积分", "兑换", "礼品", "优惠"],
            
            # SYSTEM类
            "sys_greeting": ["您好", "招商银行", "智能客服", "帮您"],
            "sys_thanks": ["不客气", "帮您", "请问"],
            "sys_bye": ["感谢", "来电", "再见"],
            "sys_offtopic": ["抱歉", "银行业务", "咨询"],
            "sys_invalid": ["抱歉", "理解", "问题", "重新"],
        }
        return keywords_map.get(intent, ["银行", "客服", "帮助"])
    
    def generate_dataset(self, total: int = 400) -> List[Dict]:
        """
        生成完整数据集
        
        分布策略：
        - INFO类: 25% (100条)
        - BIZ类: 20% (80条)
        - CONSULT类: 20% (80条)
        - SECURITY类: 15% (60条) [P0]
        - SALES类: 8% (32条)
        - SYSTEM类: 12% (48条)
        """
        
        distribution = {
            "INFO": 0.25,
            "BIZ": 0.20,
            "CONSULT": 0.20,
            "SECURITY": 0.15,
            "SALES": 0.08,
            "SYSTEM": 0.12,
        }
        
        # 按分类分配意图
        intent_pool = {
            "INFO": [
                "info_acc_balance", "info_acc_detail", "info_bill_amount", "info_bill_date",
                "info_bill_min", "info_bill_point", "info_tran_record", "info_tran_status",
                "info_branch", "info_phone", "info_hour",
            ],
            "BIZ": [
                "biz_card_loss", "biz_card_activate", "biz_card_reissue", "biz_card_eject",
                "biz_pwd_reset", "biz_pwd_change", "biz_tran_internal", "biz_tran_external",
                "biz_tran_reverse", "biz_pay_repay", "biz_pay_autopay", "biz_pay_overdue",
                "biz_installment",
            ],
            "CONSULT": [
                "cons_prod_wealth", "cons_prod_loan", "cons_prod_credit", "cons_prod_compare",
                "cons_fee_tran", "cons_fee_withdrw", "cons_fee_install",
                "cons_comp_service", "cons_comp_delay", "cons_comp_error", "cons_comp_refuse",
                "cons_urg_loss", "cons_urg_lock", "cons_urg_human",
            ],
            "SECURITY": [
                "sec_stolen_card", "sec_stolen_info", "sec_fraud_report", "sec_fraud_suspect",
                "sec_fraud_phishing", "sec_freeze_unexpected", "sec_freeze_request",
            ],
            "SALES": [
                "sales_wealth_prod", "sales_loan_prod", "sales_credit_prod",
                "sales_promo_discount", "sales_credit_point",
            ],
            "SYSTEM": [
                "sys_greeting", "sys_thanks", "sys_bye", "sys_invalid", "sys_offtopic",
            ],
        }
        
        samples = []
        
        for category, ratio in distribution.items():
            count = int(total * ratio)
            intents = intent_pool.get(category, [])
            
            for i in range(count):
                intent = random.choice(intents)
                sample = self.generate_sample(intent, category, intent)
                if sample:
                    samples.append(asdict(sample))
        
        # 打乱顺序
        random.shuffle(samples)
        
        # 重新编号
        for i, sample in enumerate(samples):
            sample["id"] = f"EVAL_{i+1:04d}"
        
        # 确保总数正确
        while len(samples) < total:
            category = random.choice(list(distribution.keys()))
            intent = random.choice(intent_pool[category])
            sample = self.generate_sample(intent, category, intent)
            if sample:
                sample["id"] = f"EVAL_{len(samples)+1:04d}"
                samples.append(asdict(sample))
        
        return samples[:total]
    
    def save(self, samples: List[Dict], path: str):
        """保存数据集"""
        data = {
            "dataset_version": "v2.0",
            "total_samples": len(samples),
            "generated_date": "2026-05-31",
            "description": "招商银行智能客服评测数据集 v2.0 - 真实场景口语化",
            "categories": {
                "INFO": sum(1 for s in samples if s["category"] == "INFO"),
                "BIZ": sum(1 for s in samples if s["category"] == "BIZ"),
                "CONSULT": sum(1 for s in samples if s["category"] == "CONSULT"),
                "SECURITY": sum(1 for s in samples if s["category"] == "SECURITY"),
                "SALES": sum(1 for s in samples if s["category"] == "SALES"),
                "SYSTEM": sum(1 for s in samples if s["category"] == "SYSTEM"),
            },
            "samples": samples,
        }
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"数据集已生成: {len(samples)}条样本")
        print(f"保存至: {path}")


def main():
    """生成数据集"""
    generator = DatasetGeneratorV2()
    samples = generator.generate_dataset(total=400)
    generator.save(samples, "data/evaluation_dataset_v2.0.json")
    
    # 打印统计
    from collections import Counter
    categories = Counter(s["category"] for s in samples)
    print("\n=== 数据分布 ===")
    for cat, count in categories.most_common():
        print(f"  {cat}: {count}条 ({count/400*100:.1f}%)")


if __name__ == "__main__":
    main()