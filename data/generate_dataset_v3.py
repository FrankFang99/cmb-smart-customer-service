"""
招商银行智能客服评测数据集生成器 v3.0
基于评测评分标准 v3.0
包含真实复杂场景样例，支持人工标注格式
"""
import json
import random
from typing import List, Dict, Any
from dataclasses import dataclass, asdict


@dataclass
class EvalSample:
    """评测样本（人工标注版）"""
    id: str
    category: str
    sub_category: str
    intent: str
    question: str
    scenario_context: str  # 场景背景
    expected_response_type: str
    required_dimensions: Dict[str, str]  # 各维度必须满足的要求
    ground_truth_keywords: List[str]
    difficulty: str
    emotion: str
    is_p0: bool


class DatasetGeneratorV3:
    """评测数据集生成器 v3.0"""
    
    def __init__(self):
        self.samples = []
        self.sample_counter = 0
        self._init_complex_scenarios()
    
    def _init_complex_scenarios(self):
        """初始化真实复杂场景"""
        
        # ============================================
        # SECURITY类 - P0场景（必须转人工）
        # ============================================
        
        self.complex_scenarios = {
            "sec_stolen_card": [
                {
                    "question": "我的卡一直在身上怎么突然有消费！境外酒店消费一万二我没出过国！",
                    "scenario_context": "用户信用卡在境外被盗刷，金额约12000元，持卡人在家刚看到消费通知，情绪非常激动",
                    "expected_response_type": "P0紧急处理",
                    "required_dims": {
                        "comprehensive_identification": "必须识别为盗刷紧急场景，识别用户情绪为激动，识别金额为12000元",
                        "response_effectiveness": "必须给出立即冻结卡片的具体操作指引，并引导报案",
                        "tool_application": "需调用账户冻结工具和投诉工单创建",
                        "copywriting_experience": "语气坚定有紧迫感，同时展现共情，不冷漠不机械",
                        "compliance_risk": "必须包含：1)卡片冻结流程 2)报案材料准备 3)48小时赔付条款"
                    },
                    "keywords": ["95555", "立即冻结", "境外消费", "盗刷", "48小时", "报案", "赔付"],
                    "difficulty": "hard",
                    "emotion": "angry"
                },
                {
                    "question": "刚才收到短信说我在美国买了东西可是卡就在包里！这是怎么回事啊？",
                    "scenario_context": "用户收到疑似伪卡交易通知，时间是凌晨3点，用户睡眼惺忪看到短信",
                    "expected_response_type": "P0紧急处理",
                    "required_dims": {
                        "comprehensive_identification": "识别为疑似伪卡/盗刷，识别时间敏感（凌晨）",
                        "response_effectiveness": "给出紧急冻结指引，说明可能原因（伪卡复制等）",
                        "tool_application": "调用冻结工具",
                        "copywriting_experience": "安抚情绪，解释可能原因，不让用户过度恐慌",
                        "compliance_risk": "包含冻结流程和后续验证要求"
                    },
                    "keywords": ["冻结", "95555", "交易验证", "伪卡", "非本人交易"],
                    "difficulty": "medium",
                    "emotion": "confused"
                },
                {
                    "question": "你们银行怎么搞的我卡没丢钱没了！一天之间被人刷了8000多块！",
                    "scenario_context": "用户是中年男性，对银行有一定信任度，突然发现多笔不明消费，情绪愤怒但希望先解决问题",
                    "expected_response_type": "P0紧急处理",
                    "required_dims": {
                        "comprehensive_identification": "识别为盗刷事件，识别损失金额8000+，识别用户愤怒但理性",
                        "response_effectiveness": "立即给出冻结+查明细+报案完整流程",
                        "tool_application": "调用冻结工具，查询近期交易明细",
                        "copywriting_experience": "态度诚恳，先道歉后处理，不推卸责任",
                        "compliance_risk": "包含完整处理流程和承诺跟进"
                    },
                    "keywords": ["冻结", "明细", "报案", "先行赔付", "跟进处理"],
                    "difficulty": "medium",
                    "emotion": "angry"
                }
            ],
            
            "sec_fraud_report": [
                {
                    "question": "我被骗了！刚转了3万块给一个说是你们银行的人！说是帮我做账户升级！",
                    "scenario_context": "用户接到诈骗电话，冒充银行客服引导转账，已转账3万元，发现被骗后立即拨打",
                    "expected_response_type": "P0紧急处理",
                    "required_dims": {
                        "comprehensive_identification": "识别为电信诈骗，已完成转账，金额3万，时间可能很近",
                        "response_effectiveness": "1)立即协助冻结收款账户 2)引导报警 3)说明资金追回可能性 4)提供反诈中心联系方式",
                        "tool_application": "协助发起账户冻结（虽然可能已晚），创建诈骗举报工单",
                        "copywriting_experience": "语气坚定专业，不给虚假希望但也不冷漠，要给予实际帮助",
                        "compliance_risk": "必须包含：1)报警流程 2)银行不会索要密码 3)反诈专线96110"
                    },
                    "keywords": ["96110", "110", "冻结收款账户", "诈骗举报", "银行不会索要密码", "转账后难以追回"],
                    "difficulty": "hard",
                    "emotion": "panic"
                },
                {
                    "question": "收到一条短信说我的卡被冻结了要我点链接重新激活，你们是真的吗？",
                    "scenario_context": "用户收到钓鱼短信，不确定真假，身边朋友曾被骗过，现在很警惕但也有点担心",
                    "expected_response_type": "风险提示+反诈教育",
                    "required_dims": {
                        "comprehensive_identification": "识别为钓鱼短信咨询，用户警惕但不确定",
                        "response_effectiveness": "明确告知是钓鱼短信，提供正确激活渠道，解释银行不会发这种短信",
                        "tool_application": "无需调用工具，但需要提供官方链接",
                        "copywriting_experience": "清晰解释，不嘲讽用户，温和但坚定地指出这是诈骗",
                        "compliance_risk": "必须包含：1)钓鱼短信识别要点 2)正确激活方式 3)如何举报此类短信"
                    },
                    "keywords": ["钓鱼短信", "95555核实", "不要点击", "举报", "95555官方"],
                    "difficulty": "medium",
                    "emotion": "anxious"
                }
            ],
            
            "cons_urg_human": [
                {
                    "question": "我要转人工！你们这个机器根本听不懂我说话！我说的是挂失不是查余额！",
                    "scenario_context": "用户连续3次尝试获得帮助但AI都理解错了，已经很烦躁，声音里带着愤怒",
                    "expected_response_type": "立即转人工",
                    "required_dims": {
                        "comprehensive_identification": "识别用户多次失败的历史，识别当前情绪为愤怒/挫败",
                        "response_effectiveness": "不再尝试解释，果断转人工，过程中保持友好",
                        "tool_application": "调用转人工工具，记录用户问题便于人工接手",
                        "copywriting_experience": "道歉真诚，不辩解不推脱，快速执行转接",
                        "compliance_risk": "快速转接是核心，不能让用户继续等待"
                    },
                    "keywords": ["转人工", "道歉", "立即转接", "记录问题"],
                    "difficulty": "easy",
                    "emotion": "angry"
                },
                {
                    "question": "算了不跟你们机器聊了，浪费时间，给我转能说话的人",
                    "scenario_context": "用户是老年人，觉得跟机器对话不习惯，更信任真人",
                    "expected_response_type": "转人工",
                    "required_dims": {
                        "comprehensive_identification": "识别为老年用户，不适应AI交互，明确要求人工",
                        "response_effectiveness": "尊重用户选择，快速转人工，不强推自助服务",
                        "tool_application": "调用转人工工具",
                        "copywriting_experience": "尊重有礼貌，语速适当，承认AI的局限性",
                        "compliance_risk": "满足用户转人工需求，不设置障碍"
                    },
                    "keywords": ["转人工", "老年人", "尊重选择"],
                    "difficulty": "easy",
                    "emotion": "neutral"
                }
            ],
            
            "cons_comp_service": [
                {
                    "question": "我跟你们反映了三次同样的问题每次都说记录了会处理，结果三天过去了没任何反馈！你们到底有没有在处理？！",
                    "scenario_context": "用户之前投诉过，等待三天没有结果，现在非常不满，要求升级处理",
                    "expected_response_type": "投诉升级处理",
                    "required_dims": {
                        "comprehensive_identification": "识别为升级投诉，识别历史问题（3次反馈未解决），识别等待时间3天",
                        "response_effectiveness": "1)立即查看工单状态 2)给出具体处理时间承诺 3)承诺主动回呼",
                        "tool_application": "查询工单状态，创建升级工单，标记紧急",
                        "copywriting_experience": "真诚道歉，承认服务不足，承诺改进",
                        "compliance_risk": "记录完整投诉历史，承诺的回呼必须兑现"
                    },
                    "keywords": ["升级处理", "工单查询", "回呼承诺", "加急", "主管跟进"],
                    "difficulty": "medium",
                    "emotion": "angry"
                },
                {
                    "question": "你们柜员那个态度真的太差了，问她问题爱理不理，翻白眼给我看！我要投诉！",
                    "scenario_context": "用户到网点办业务遇到服务态度问题，现在通过电话投诉，情绪激动但希望得到重视",
                    "expected_response_type": "投诉受理",
                    "required_dims": {
                        "comprehensive_identification": "识别为服务态度投诉，涉及网点人员，需要工号或时间定位",
                        "response_effectiveness": "1)认真倾听并记录 2)承诺调查核实 3)给予投诉编号方便跟进",
                        "tool_application": "创建投诉工单，记录时间地点人员",
                        "copywriting_experience": "态度认真，展现同理心，让用户感受到被重视",
                        "compliance_risk": "不否认也不立即确认事实，承诺调查后反馈"
                    },
                    "keywords": ["投诉工单", "调查", "反馈", "网点名称", "时间"],
                    "difficulty": "medium",
                    "emotion": "angry"
                }
            ],
            
            "biz_tran_external": [
                {
                    "question": "我要跨行转账30万给客户，能不能实时到账？手续费多少？",
                    "scenario_context": "用户做生意的，需要大额转账给供应商，对到账时间有要求（客户催了），金额30万不小",
                    "expected_response_type": "业务咨询+风险提示",
                    "required_dims": {
                        "comprehensive_identification": "识别为大额转账（30万），行外转账，实时到账需求，商务场景",
                        "response_effectiveness": "1)说明到账时间（工作日/实时）2)手续费计算方式 3)大额转账风险提示",
                        "tool_application": "查询实时转账可用性和手续费",
                        "copywriting_experience": "专业清晰，帮助用户做决策，提供多个方案",
                        "compliance_risk": "⚠️ 必须包含：大额转账风险提示（核实收款人、警惕诈骗）、转账后无法撤回"
                    },
                    "keywords": ["跨行转账", "手续费", "实时到账", "大额风险", "核实收款人", "无法撤回"],
                    "difficulty": "medium",
                    "emotion": "urgent"
                },
                {
                    "question": "帮朋友转账转错了，10万块打到一个陌生账户去了，能不能帮我追回来？",
                    "scenario_context": "用户帮朋友操作转账，输错了账号转错了人，朋友在旁边很着急",
                    "expected_response_type": "紧急情况处理",
                    "required_dims": {
                        "comprehensive_identification": "识别为转账错误，金额10万，陌生账户，用户（帮人）操作",
                        "response_effectiveness": "1)说明无法直接撤回 2)提供可能的解决路径 3)建议报警处理",
                        "tool_application": "查询转账状态，看是否已清算",
                        "copywriting_experience": "表达理解帮助之心，不给虚假的希望但给出实际方案",
                        "compliance_risk": "⚠️ 转账后无法撤回是核心，必须强调核实信息的重要性"
                    },
                    "keywords": ["无法撤回", "报警", "收款银行", "追回可能性", "核实信息"],
                    "difficulty": "hard",
                    "emotion": "anxious"
                }
            ],
            
            "cons_prod_wealth": [
                {
                    "question": "我有50万闲钱想投资，你们有什么理财产品推荐吗？要安全一点的",
                    "scenario_context": "用户是中年企业家，50万是闲钱，希望保值增值，对风险有一定认识但不追求高收益",
                    "expected_response_type": "产品咨询+风险揭示",
                    "required_dims": {
                        "comprehensive_identification": "识别为理财咨询，金额50万，安全偏好，无明确期限",
                        "response_effectiveness": "1)了解风险偏好 2)介绍适合产品类型 3)说明收益和风险关系",
                        "tool_application": "查询当前理财产品列表，按风险等级筛选",
                        "copywriting_experience": "专业有耐心，不推销，引导用户了解产品后再决定",
                        "compliance_risk": "⚠️ 必须包含：理财非存款、投资有风险、具体收益不代表实际"
                    },
                    "keywords": ["理财有风险", "风险测评", "产品类型", "收益不代表实际", "50万起投"],
                    "difficulty": "medium",
                    "emotion": "neutral"
                },
                {
                    "question": "我之前买的那个理财产品现在亏了5万块了，怎么办？能退吗？",
                    "scenario_context": "用户之前买了净值型理财，市场波动亏损，心理焦虑但还没恐慌",
                    "expected_response_type": "理财亏损咨询",
                    "required_dims": {
                        "comprehensive_identification": "识别为净值型理财亏损咨询，识别亏损金额5万，识别用户焦虑但理性",
                        "response_effectiveness": "1)解释净值波动正常现象 2)说明持有/赎回的不同后果 3)不承诺回本",
                        "tool_application": "查询持仓情况和当前净值",
                        "copywriting_experience": "安抚情绪但不说假话，客观分析利弊，让用户自己做决定",
                        "compliance_risk": "⚠️ 不能承诺回本，不能暗示银行会兜底"
                    },
                    "keywords": ["净值波动", "持有到期", "赎回损失", "市场风险", "不承诺回本"],
                    "difficulty": "hard",
                    "emotion": "anxious"
                }
            ],
            
            "cons_prod_loan": [
                {
                    "question": "我想贷款100万做生意，什么产品最适合我？利率多少？",
                    "scenario_context": "用户是小微企业主，想贷款扩大经营，对贷款产品和利率不了解，需要专业建议",
                    "expected_response_type": "贷款产品咨询",
                    "required_dims": {
                        "comprehensive_identification": "识别为贷款咨询，金额100万，用途做生意，需要了解还款能力",
                        "response_effectiveness": "1)了解经营情况 2)介绍适合产品 3)说明利率和还款方式",
                        "tool_application": "查询贷款产品列表，准备贷款计算器",
                        "copywriting_experience": "专业但接地气，不夸大贷款优势，提醒理性借贷",
                        "compliance_risk": "⚠️ 必须包含：贷款需谨慎评估还款能力、利率以实际审批为准"
                    },
                    "keywords": ["还款能力", "贷款计算器", "利率以审批为准", "企业经营贷款", "谨慎借贷"],
                    "difficulty": "medium",
                    "emotion": "neutral"
                },
                {
                    "question": "我信用卡欠了20万还不上了，最低还款也还不起，怎么办？会不会坐牢？",
                    "scenario_context": "用户信用卡逾期严重，财务危机，可能有恐慌心理",
                    "expected_response_type": "危机处理+专业引导",
                    "required_dims": {
                        "comprehensive_identification": "识别为严重逾期（20万），识别用户恐慌（担心法律后果）",
                        "response_effectiveness": "1)安抚情绪 2)说明法律后果（合理说明，不夸大）3)提供解决方案路径",
                        "tool_application": "查询欠款金额，计算最低还款额和逾期费用",
                        "copywriting_experience": "温和不恐慌，给出希望但不说假话，引导专业机构介入",
                        "compliance_risk": "⚠️ 不能说坐牢等误导性话术，引导联系银行协商或寻求法律帮助"
                    },
                    "keywords": ["协商还款", "分期偿还", "法律帮助", "不坐牢", "银行协商"],
                    "difficulty": "hard",
                    "emotion": "panic"
                }
            ],
            
            "info_bill_amount": [
                {
                    "question": "我的信用卡本期账单多少？最低还款多少？分期手续费怎么算？",
                    "scenario_context": "用户月底查账单，想了解具体金额和还款方式，在外出差用手机查询",
                    "expected_response_type": "账单查询",
                    "required_dims": {
                        "comprehensive_identification": "识别为账单查询需求，需要具体金额和分期信息",
                        "response_effectiveness": "准确给出账单金额、最低还款、分期手续费",
                        "tool_application": "查询信用卡账单信息",
                        "copywriting_experience": "清晰简洁，让用户快速获取所需信息",
                        "compliance_risk": "包含最低还款和分期的风险提示"
                    },
                    "keywords": ["账单金额", "最低还款", "分期手续费", "还款日"],
                    "difficulty": "easy",
                    "emotion": "neutral"
                }
            ],
            
            "biz_card_loss": [
                {
                    "question": "我的信用卡在餐厅丢了，被人捡走了可能会被盗刷，我在外地出差回不去怎么办！",
                    "scenario_context": "用户在外出差，信用卡丢失，可能已被他人捡走，有被盗刷风险",
                    "expected_response_type": "紧急挂失",
                    "required_dims": {
                        "comprehensive_identification": "识别为紧急挂失场景，用户在外地，无法立即返回",
                        "response_effectiveness": "1)立即协助挂失 2)说明后续补卡流程 3)承诺风险承担",
                        "tool_application": "立即执行挂失操作，创建补卡工单",
                        "copywriting_experience": "紧迫感强，主动帮用户做紧急处理，让用户安心",
                        "compliance_risk": "包含挂失后风险赔付说明"
                    },
                    "keywords": ["立即挂失", "赔付", "补卡", "95555", "48小时内"],
                    "difficulty": "medium",
                    "emotion": "urgent"
                }
            ]
        }
        
        # 简单场景模板（用于填充数量）
        self.simple_templates = {
            "info_acc_balance": ["余额多少", "查一下卡里还有多少钱", "剩多少"],
            "info_bill_date": ["还款日是几号", "最晚什么时候还", "截止日期"],
            "biz_card_activate": ["怎么激活新卡", "开卡流程是什么", "卡片激活"],
            "biz_pwd_reset": ["密码忘了怎么办", "忘记密码怎么重置", "密码不记得了"],
            "sys_greeting": ["你好", "在吗", "你好啊"],
            "sys_thanks": ["谢谢", "感谢", "好的知道了"],
        }
    
    def generate_dataset(self, total: int = 400, complex_ratio: float = 0.3) -> List[Dict]:
        """
        生成完整数据集
        
        Args:
            total: 总样本数
            complex_ratio: 复杂场景占比（默认30%）
        """
        samples = []
        
        # 目标分布
        target_distribution = {
            "SECURITY": 60,      # 15% - P0高权重
            "CONSULT": 80,       # 20% - 投诉紧急
            "BIZ": 80,          # 20% - 业务办理
            "INFO": 80,         # 20% - 查询
            "SALES": 40,        # 10% - 营销
            "SYSTEM": 60,       # 15% - 简单场景
        }
        
        # 生成复杂场景（重复使用以达到目标数量）
        for scenario_type, cases in self.complex_scenarios.items():
            category = self._get_category(scenario_type)
            target = target_distribution.get(category, 0)
            if target <= 0:
                continue
            
            # 计算需要重复的次数
            repeat_times = (target // len(cases)) + 1
            for _ in range(repeat_times):
                for case in cases:
                    if target_distribution.get(category, 0) <= 0:
                        break
                    
                self.sample_counter += 1
                sample = {
                    "id": f"EVAL_{self.sample_counter:04d}",
                    "category": category,
                    "sub_category": scenario_type,
                    "intent": scenario_type,
                    "question": case["question"],
                    "scenario_context": case["scenario_context"],
                    "expected_response_type": case["expected_response_type"],
                    "required_dimensions": case["required_dims"],
                    "ground_truth_keywords": case["keywords"],
                    "difficulty": case["difficulty"],
                    "emotion": case["emotion"],
                    "is_p0": self._is_p0_intent(scenario_type),
                    "manual_scores": {
                        "comprehensive_identification": None,
                        "response_effectiveness": None,
                        "tool_application": None,
                        "copywriting_experience": None,
                        "compliance_risk": None,
                        "total_score": None,
                        "rating": None,
                        "annotator": None,
                        "annotate_time": None
                    },
                    "llm_scores": {
                        "comprehensive_identification": None,
                        "response_effectiveness": None,
                        "tool_application": None,
                        "copywriting_experience": None,
                        "compliance_risk": None,
                        "total_score": None,
                        "rating": None
                    }
                }
                samples.append(sample)
                target_distribution[category] -= 1
        
        # 生成简单场景填充
        simple_templates = {
            "INFO": [
                ("余额多少", "查询账户余额"),
                ("还款日是几号", "查询还款日期"),
                ("账单多少", "查询账单金额"),
                ("积分多少", "查询积分"),
                ("网点在哪", "查询网点地址"),
                ("手续费多少", "查询手续费"),
            ],
            "BIZ": [
                ("怎么激活卡", "卡片激活流程"),
                ("密码忘了怎么办", "密码重置"),
                ("挂失怎么操作", "卡片挂失"),
                ("转账多久到账", "转账进度查询"),
            ],
            "CONSULT": [
                ("利率多少", "利率咨询"),
                ("分期手续费多少", "分期咨询"),
                ("投诉", "投诉处理"),
                ("转人工", "转接人工"),
            ],
            "SALES": [
                ("有什么理财产品", "产品推荐"),
                ("贷款产品有哪些", "贷款咨询"),
                ("信用卡优惠", "活动咨询"),
            ],
            "SYSTEM": [
                ("你好", "问候"),
                ("谢谢", "感谢"),
                ("再见", "告别"),
                ("查一下余额", "查询"),
            ]
        }
        
        for category, templates in simple_templates.items():
            while target_distribution.get(category, 0) > 0 and len(samples) < total:
                template = templates[len(samples) % len(templates)]
                self.sample_counter += 1
                sample = {
                    "id": f"EVAL_{self.sample_counter:04d}",
                    "category": category,
                    "sub_category": template[1],
                    "intent": template[1].lower().replace(" ", "_"),
                    "question": template[0],
                    "scenario_context": "简单查询场景",
                    "expected_response_type": "标准业务处理",
                    "required_dimensions": {
                        "comprehensive_identification": "识别用户查询意图",
                        "response_effectiveness": "给出准确的业务回答",
                        "tool_application": "按需调用查询工具",
                        "copywriting_experience": "简洁专业",
                        "compliance_risk": "无特殊合规要求"
                    },
                    "ground_truth_keywords": ["银行", "客服", "帮助"],
                    "difficulty": "easy",
                    "emotion": "neutral",
                    "is_p0": False,
                    "manual_scores": {
                        "comprehensive_identification": None,
                        "response_effectiveness": None,
                        "tool_application": None,
                        "copywriting_experience": None,
                        "compliance_risk": None,
                        "total_score": None,
                        "rating": None,
                        "annotator": None,
                        "annotate_time": None
                    },
                    "llm_scores": {
                        "comprehensive_identification": None,
                        "response_effectiveness": None,
                        "tool_application": None,
                        "copywriting_experience": None,
                        "compliance_risk": None,
                        "total_score": None,
                        "rating": None
                    }
                }
                samples.append(sample)
                target_distribution[category] -= 1
        
        # 打乱顺序
        random.shuffle(samples)
        
        # 重新编号
        for i, sample in enumerate(samples):
            sample["id"] = f"EVAL_{i+1:04d}"
        
        return samples[:total]
    
    def _get_category(self, intent: str) -> str:
        """获取意图对应的一级分类"""
        if intent.startswith("sec_"):
            return "SECURITY"
        elif intent.startswith("cons_urg") or intent.startswith("cons_comp"):
            return "CONSULT"
        elif intent.startswith("cons_"):
            return "CONSULT"
        elif intent.startswith("biz_"):
            return "BIZ"
        elif intent.startswith("info_"):
            return "INFO"
        elif intent.startswith("sales_"):
            return "SALES"
        else:
            return "SYSTEM"
    
    def _is_p0_intent(self, intent: str) -> bool:
        """判断是否为P0意图"""
        p0_intents = [
            "sec_stolen_card", "sec_stolen_info", "sec_fraud_report", "sec_fraud_suspect",
            "sec_fraud_phishing", "sec_freeze_unexpected", "sec_freeze_request",
            "cons_urg_human", "cons_urg_loss", "cons_urg_lock",
            "cons_comp_service", "cons_comp_delay", "cons_comp_error"
        ]
        return intent in p0_intents
    
    def save(self, samples: List[Dict], path: str):
        """保存数据集"""
        data = {
            "dataset_version": "v3.0",
            "total_samples": len(samples),
            "generated_date": "2026-05-31",
            "description": "招商银行智能客服评测数据集 v3.0 - 支持人工标注格式",
            "categories": {
                "INFO": sum(1 for s in samples if s["category"] == "INFO"),
                "BIZ": sum(1 for s in samples if s["category"] == "BIZ"),
                "CONSULT": sum(1 for s in samples if s["category"] == "CONSULT"),
                "SECURITY": sum(1 for s in samples if s["category"] == "SECURITY"),
                "SALES": sum(1 for s in samples if s["category"] == "SALES"),
                "SYSTEM": sum(1 for s in samples if s["category"] == "SYSTEM"),
            },
            "complex_scenarios_count": sum(1 for s in samples if s["difficulty"] == "hard"),
            "p0_count": sum(1 for s in samples if s["is_p0"]),
            "samples": samples,
        }
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"数据集已生成: {len(samples)}条样本")
        print(f"复杂场景: {data['complex_scenarios_count']}条")
        print(f"P0场景: {data['p0_count']}条")
        print(f"保存至: {path}")


def main():
    """生成数据集"""
    generator = DatasetGeneratorV3()
    samples = generator.generate_dataset(total=200)  # 先生成200条，复杂场景多
    generator.save(samples, "data/evaluation_dataset_v3.0.json")
    
    # 打印统计
    from collections import Counter
    categories = Counter(s["category"] for s in samples)
    p0_count = sum(1 for s in samples if s["is_p0"])
    hard_count = sum(1 for s in samples if s["difficulty"] == "hard")
    
    print("\n=== 数据分布 ===")
    for cat, count in categories.most_common():
        print(f"  {cat}: {count}条 ({count/len(samples)*100:.1f}%)")
    print(f"\nP0场景: {p0_count}条")
    print(f"复杂场景: {hard_count}条")


if __name__ == "__main__":
    main()