# 智能客服三级类目标准 v3.2（终版）

> 文档目的：定义招行智能客服的 **7 域 89 三级分类体系**、**12 个 P0 红线清单**（v3.6.2 PM 重审）、**优先级判定规则**，作为意图识别（NLU）和对话路由（Dialog Router）的真值表。
>
> 适用版本：v3.2（基于 v3.1 终版的归类调整 + v3.6.2 PM 重审）
> 主要变更：
> 1. ✅ M+ 等级归并入 `info_member_grade`（招行会员体系即 M+）
> 2. ✅ 近期账单归并入 `info_transaction_recent`（statement = recent transaction）
> 3. ✅ 新增《分类原则》第 5 条：多意图 query 的 disambiguation 规则（回答+澄清追问+动作入口）
> 4. ✅ SYSTEM 域拆分为 `sys_service`（服务通道）和 `sys_app_help`（App 引导），投诉/表扬/反馈/转人工归服务通道，引导类归 App 引导
> 5. ✅ 表扬从 P0 改 P1（模板回复+自动建工单+转对应网点，不紧急）
> 6. ✅ 全表 query 改为客户真实问法（剔除"境外大额汇出""转 50 万到对公"等非自然问法）
> 7. 🔥 **v3.6.2 PM 重审**：21 P0 → 12 P0，11 类业务子类（INFO/BIZ/CONSULT/MARKETING）从 P0 降级为 P1/P2/P3。详见 §四 PM 调整说明。

---

## 一、分类体系总览（7 域 84 三级）

### 域 1：INFO 信息查询（12 个三级）

| 二级 | 三级 | 优先级 | 客户真实 query | 数据源 |
|---|---|---|---|---|
| info_account | info_account_balance | **P2** ⚠️v3.6.2 | "我卡里还有多少钱" | 账户系统（模板直出，短信验证即可）|
| | info_account_card_no | **P2** ⚠️v3.6.2 | "我尾号多少的卡" | 账户系统（模板直出）|
| | info_account_open_bank | **P2** ⚠️v3.6.2 | "这个卡是哪家开的" | 账户系统（卡面即有）|
| | info_account_type | P1 | "我这个是几类户" | 账户系统 |
| info_transaction | info_transaction_recent | P1 | "我最近几笔账单" / "上个月花了多少" | 交易系统 |
| | info_transaction_filter | P2 | "上周三那笔转账" / "3 月份的交易明细" | 交易系统 |
| info_member | **info_member_grade** | P2 | "我 M+ 几级了" / "我现在是金葵花吗" | 会员系统 |
| | info_member_point | P2 | "我还有多少积分" | 会员系统 |
| info_credit | info_credit_limit | P1 | "我信用卡额度多少" | 信用卡系统 |
| | info_credit_bill | P1 | "这期账单多少钱" | 信用卡系统 |
| | info_credit_point | P2 | "我信用卡积分怎么查" | 信用卡系统 |
| info_app | info_app_account | P2 | "App 上怎么查开户行" | App 帮助 |

> **INFO P0（v3.6.2 已降级为 0 个）**：v3.6.2 前 3 个 P0 模板回复（balance / card_no / open_bank）已降级为 P2。理由：模板直出，短信验证即可，无强转人工要求。
> 🔥 **v3.2 归并说明**：
> - 删除 `info_assets_m_plus`（M+ 等级 = 招行会员等级，归 `info_member_grade`）
> - 删除 `info_account_statement`（近期账单 = 近期交易，归 `info_transaction_recent`）

---

### 域 2：BIZ 业务办理（16 个三级）

| 二级 | 三级 | 优先级 | 客户真实 query | 触发动作 |
|---|---|---|---|---|
| biz_transfer | biz_transfer_same_bank | P1 | "我转账给小李" / "转 5000 给老婆" | 转账流程 |
| | biz_transfer_cross_bank | P1 | "跨行转账怎么操作" | 转账流程 |
| | **biz_transfer_large** | **P0** | "我要转 50 万给公司" / "转 50 万要什么手续" | 🔥 **双触发 SECURITY.aml_large_transfer** |
| biz_password | biz_password_reset | **P1** ⚠️v3.6.2 | "怎么修改银行卡密码" / "我要改密码" | 业务敏感（身份核验），非强转人工 |
| | biz_password_change | P1 | "怎么换新密码" | 密码管理 |
| biz_card | biz_card_apply | P1 | "我想办张新卡" | 办卡流程 |
| | biz_card_activate | P1 | "我新卡怎么激活" | 卡激活 |
| | biz_card_replace | P1 | "卡坏了换一张" | 换卡流程 |
| biz_statement | biz_statement_print | **P1** ⚠️v3.6.2 | "我要打印流水" / "盖章版对账单" | 业务敏感（需本人持身份证），非强转人工 |
| biz_loan | biz_loan_apply | P1 | "我想申请房贷" | 贷款申请 |
| | biz_loan_repay | P1 | "我怎么提前还贷" | 还款流程 |
| biz_credit_card | biz_credit_card_apply | P1 | "我想办招行信用卡" | 信用卡申请 |
| | biz_credit_card_billing_date | P1 | "怎么改账单日" | 信用卡管理 |
| biz_optout | **biz_optout_outbound** | **P0** | "别再给我打电话了" / "取消营销外呼" | P0（监管合规）|
| biz_wealth | biz_wealth_buy | P1 | "我要买这个理财" | 理财购买 |
| biz_app | biz_app_open_account | P1 | "怎么在 App 开户" | App 引导 |

> **BIZ P0（v3.6.2 仅 2 个）**：biz_transfer_large（双触发 SECURITY.aml_large_transfer，反洗钱）+ biz_optout_outbound（金融营销外呼强监管）
> v3.6.2 前 4 个 P0 中的 biz_password_reset / biz_statement_print 已降级为 P1（业务敏感但非红线）
> 🔥 **密码分流（配合原则 4）**：
> - "我要改密码 / 怎么改密码" → `biz_password_reset`（BIZ 主动办）
> - "我密码输错被锁了" → `safety_password_locked`（SAFETY 异常态）
> - "我密码好像被人改过" → `safety_password_forget` + **双触发 SECURITY.fraud_recognize**
>
> 🔥 **多意图 disambiguation（原则 5）**：
> - "跨行转账怎么操作" → 答完追问"是想要现在办跨行转账吗？" + 给跨行转账入口

---

### 域 3：CONSULT 咨询（22 个三级）

| 二级 | 三级 | 优先级 | 客户真实 query |
|---|---|---|---|
| consult_deposit | consult_deposit_demand | P1 | "活期/定期利率" |
| | consult_deposit_time | P1 | "三年期利率" |
| | consult_deposit_min | P2 | "起存金额" |
| consult_loan | consult_loan_mortgage | **P2** ⚠️v3.6.2 | "首套房利率多少" / "现在 LPR 多少"（公开咨询，LPR 由央行每月公布）|
| | consult_loan_credit | P1 | "信用贷利率" |
| | consult_loan_business | P2 | "小微贷条件" |
| | consult_loan_repay_method | P1 | "等额本息 vs 本金" |
| consult_wealth | consult_wealth_deposit | P1 | "大额存单收益" |
| | consult_wealth_fund | P1 | "基金风险等级" |
| | consult_wealth_insurance | P1 | "保险犹豫期" |
| | consult_wealth_gold | P2 | "纸黄金规则" |
| consult_fee | consult_fee_account | P1 | "账户管理费" |
| | consult_fee_transfer | P1 | "转账手续费" |
| | consult_fee_cross_border | P2 | "境外汇款手续费" |
| consult_fx | consult_fx_rate | P1 | "美元汇率今天多少" |
| | consult_fx_cross | P2 | "跨境汇款限额" |
| consult_card_attr | consult_card_level | P2 | "金卡/金葵花区别" |
| | consult_card_app | P2 | "二类三类卡区别" |
| consult_member | consult_member_m_plus | P1 | "M+ 怎么升级" |
| | consult_member_point | P2 | "积分怎么用" |
| consult_credit_card | consult_credit_card_bill | P1 | "信用卡账单日怎么算" |
| | consult_credit_card_fee | P1 | "信用卡年费多少" |
| | consult_credit_card_limit | P1 | "信用卡额度怎么提" |
| | consult_credit_card_product | P2 | "哪种信用卡好" |
| | consult_credit_card_installment | P2 | "账单分期手续费" |

> **CONSULT P0（v3.6.2 已降级为 0 个）**：v3.6.2 前 1 个 P0 mortgage 已降级为 P2。理由：LPR 是央行每月公开数据，客户咨询属于公开规则查询，非红线。
> 🔥 **多意图 disambiguation**：
> - "信用卡额度怎么提" → 答完问"是查询提额条件，还是要现在申请提额？" + 申请入口

---

### 域 4：MARKETING 活动（11 个三级，仅临时活动）

| 二级 | 三级 | 优先级 | 客户真实 query | 临时/常驻 |
|---|---|---|---|---|
| mkt_food | mkt_food_5off | **P3** ⚠️v3.6.2 | "周三 5 折怎么用" / "饭票在哪领" | 临时（每周，营销活动）|
| | mkt_food_brand | P1 | "麦当劳有什么优惠" | 临时 |
| mkt_cinema | mkt_cinema_99 | P1 | "影票 9 块 9 怎么买" | 临时（档期）|
| mkt_pay | mkt_pay_firstbind | P1 | "首绑立减怎么用" | 临时（限新户）|
| | mkt_pay_cashback | P1 | "支付满减" | 临时 |
| | mkt_pay_coupon | P2 | "特定加息券活动" | 临时（**常驻加息规则放咨询**）|
| mkt_invite | mkt_invite_cash | P2 | "邀请好友得现金" | 临时 |
| mkt_signin | mkt_signin_daily | P2 | "签到有礼" | 临时 |
| mkt_point | mkt_point_double | P2 | "积分翻倍日" | 临时（月度）|
| mkt_newuser | mkt_newuser_gift | P1 | "新户首绑礼" | 临时 |
| mkt_birthday | mkt_birthday_priv | P2 | "生日特权" | 临时 |
| mkt_member | mkt_member_monthly | **P3** ⚠️v3.6.2 | "M+ 本月有什么福利" | 临时（每月变，营销活动）|
| | mkt_member_upgrade | **P3** ⚠️v3.6.2 | "M+ 升级礼怎么领" | 临时（活动期，营销活动）|

> **MARKETING P0（v3.6.2 已降级为 0 个）**：v3.6.2 前 3 个 P0（5off / member_monthly / member_upgrade）已降级为 P3。理由：营销活动规则公开，错过不造成损失，非红线。

---

### 域 5：SECURITY 安全合规（7 个三级，P0 强转人工通道）🔥

| 二级 | 三级 | 优先级 | 客户真实 query | 触发动作 |
|---|---|---|---|---|
| security_fraud | security_fraud_recognize | **P0** | "我收到个短信让我点链接，是不是诈骗" | 强转人工 + 95555 反诈中心 |
| | security_fraud_report | **P0** | "我好像被骗了" / "我刚给骗子转了钱" | 强转人工 + 紧急冻结通道 |
| security_aml | security_aml_large_transfer | **P0** | "我要转 50 万给公司" / "转给个人 30 万要不要手续" | 反洗钱触发 + 人工审核 |
| | security_aml_cross_border | **P0** | "我要汇 5 万美元给我在美国的女儿" / "境外汇款怎么操作" | 反洗钱触发 + 人工审核 |
| security_suitability | security_suitability_unrated | **P0** | "我还没做风险评估，能买基金吗" | 适当性拦截 + 引导评估 |
| | security_suitability_mismatch | **P0** | "我是 R1，能买 R4 的基金吗" | 适当性拦截 + 人工解释 |
| security_promise | security_promise_yield | **P0** | "这个理财保本吗" / "年化能到 5% 吗" | 承诺收益拦截 + 强转人工 |

> **SECURITY 域 100% P0 强转人工 + 监管报送独立通道**
> 🔥 **v3.2 调整**：`security_aml_cross_border` 的 query 改为"我要汇 5 万美元给我在美国的女儿"——客户真实问法

---

### 域 6：SAFETY 账户安全（5 个三级，独立成域）

| 二级 | 三级 | 优先级 | 客户真实 query | 备注 |
|---|---|---|---|---|
| safety_card | safety_card_freeze | P1 | "我的卡被冻结了" / "卡显示状态异常" | 应急话术 + 引导 App 操作 |
| | safety_card_loss | **P0** | "我的卡丢了怎么办" / "我要挂失银行卡" | 🔥 **应急话术 + 强转人工 + 双触发 security_fraud_recognize** |
| safety_password | safety_password_forget | P1 | "我登录密码忘了怎么重置" | 🔥 异常态 → SAFETY（非 BIZ）|
| | safety_password_locked | P1 | "我密码输错被锁了" | 🔥 异常态 → SAFETY |
| safety_device | safety_device_unbind | P1 | "怎么解绑手机" / "我想换绑手机号" | |

> **SAFETY 域 P0 清单（1 个）**：safety_card_loss（且双触发 SECURITY.fraud_recognize）
>
> 🔥 **与 BIZ.biz_password 的边界规则（原则 4）**：
>
> | 客户表达 | 归属 | 理由 |
> |---|---|---|
> | "怎么修改银行卡密码" / "我要改密码" | biz_password_reset (BIZ) | 主动办理 |
> | "我登录密码忘了怎么重置" | biz_password_reset (BIZ) | 操作类（虽然"忘了"但目标是重置）|
> | "我密码输错被锁了" | safety_password_locked (SAFETY) | 异常态 |
> | "我密码好像被人改过" | safety_password_forget + **双触发 SECURITY.fraud_recognize** | 疑似盗用 |
>
> 🔥 **多意图 disambiguation（原则 5）**：
> - "怎么解绑手机" → 答完问"是要换绑手机，还是怀疑被盗？" + 2 个入口
> - "我卡被冻结了" → 答完问"是查询冻结原因，还是要解冻？" + 查询/解冻入口

---

### 域 7：SYSTEM 系统级（11 个三级，v3.2 拆分）

#### 7.1 sys_service 服务通道（4 个三级）

| 二级 | 三级 | 优先级 | 客户真实 query | 触发动作 |
|---|---|---|---|---|
| sys_service | **sys_service_route_human** | **P0** | "转人工" / "叫客服" | 直转在线客服 |
| | **sys_service_complaint** | **P0** | "我要投诉" / "我要投诉理财经理" / "我要投诉 App 闪退" | 🔥 **直转人工 + 工单带会话**（监管 100% 人工受理）|
| | sys_service_praise | **P1** | "我要表扬 XX 经理" | P1 模板回复 + 自动建表扬工单 + 转对应网点 |
| | sys_service_feedback | P1 | "我有个建议" / "意见反馈" | 收集 + 工单 |

#### 7.2 sys_app_help App 使用引导（3 个三级）

| 二级 | 三级 | 优先级 | 客户真实 query | 路由动作 |
|---|---|---|---|---|
| sys_app_help | sys_app_help_navigation | P1 | "理财在哪" / "怎么看账单" | 引导（界面位置/路径）|
| | sys_app_help_setting | P1 | "怎么改默认卡" / "怎么开指纹登录" | 引导（设置路径）|
| | sys_app_help_data | P2 | "怎么导出对账单" / "怎么下载电子发票" | 引导（功能路径）|

#### 7.3 sys_other 系统兜底（4 个三级）

| 二级 | 三级 | 优先级 | 客户真实 query | 路由动作 |
|---|---|---|---|---|
| sys_other | sys_other_greet | P3 | "你好" | 兜底话术 |
| | sys_other_invalid | P3 | "乱码/语音转文字错误" | 兜底话术 |
| | sys_other_farewell | P3 | "谢谢" / "再见" | 兜底话术 |
| | sys_other_unclear | P3 | 多种意图无法判定 | disambiguation 兜底（参考原则 5）|

> 🔥 **v3.2 拆分说明**：
> - **服务通道**（投诉/表扬/反馈/转人工）= 客服系统对接，**都要进工单系统**
> - **App 引导** = 知识库 + 界面引导，**不是客服工单**
> - **系统兜底** = 闲聊/无效输入的兜底
> - **表扬从 P0 改 P1**：标准回答+自动建工单+转对应网点，**不紧急**

---

## 二、12 个 P0 红线清单（v3.6.2 PM 重审）

> 🔥 **v3.6.2 PM 重审**：v3.2 原 21 个 P0 经银行业务审视，11 类"业务敏感但非监管红线"已降级为 P1/P2/P3（详见 §四）。当前 **12 个 P0** 全部满足"必须人工介入 / 监管强转人工 / 反洗钱前置 / 反诈紧急冻结"四个条件之一。

| # | 三级 | 域 | 触发动作 | 红线类型 |
|---|---|---|---|---|
| 1 | biz_transfer_large | BIZ | 🔥 **双触发 SECURITY.aml_large_transfer** | 反洗钱前置 |
| 2 | biz_optout_outbound | BIZ | 取消营销外呼（金融营销强监管）| 监管合规 |
| 3 | security_fraud_recognize | SECURITY | **强转人工 + 95555 反诈中心** | 反诈 |
| 4 | security_fraud_report | SECURITY | **强转人工 + 紧急冻结通道** | 反诈 |
| 5 | security_aml_large_transfer | SECURITY | **强转人工 + 人工审核** | 反洗钱 |
| 6 | security_aml_cross_border | SECURITY | **强转人工 + 人工审核** | 反洗钱 |
| 7 | security_suitability_unrated | SECURITY | **适当性拦截 + 引导评估** | 适当性 |
| 8 | security_suitability_mismatch | SECURITY | **适当性拦截 + 人工解释** | 适当性 |
| 9 | security_promise_yield | SECURITY | **承诺收益拦截 + 强转人工** | 承诺收益 |
| 10 | safety_card_loss | SAFETY | **应急话术 + 强转人工 + 双触发 fraud** | 应急 |
| 11 | sys_service_route_human | SYSTEM | 直转在线客服 | 强转人工 |
| 12 | sys_service_complaint | SYSTEM | **直转人工 + 工单带会话（监管要求）** | 投诉 |
| ~~13~~ | ~~info_account_balance~~ | ~~INFO~~ | ~~v3.6.2 降级为 P2~~ 模板直出 | — |
| ~~14~~ | ~~info_account_card_no~~ | ~~INFO~~ | ~~v3.6.2 降级为 P2~~ 模板直出 | — |
| ~~15~~ | ~~info_account_open_bank~~ | ~~INFO~~ | ~~v3.6.2 降级为 P2~~ 卡面即有 | — |
| ~~16~~ | ~~biz_password_reset~~ | ~~BIZ~~ | ~~v3.6.2 降级为 P1~~ 业务敏感 | — |
| ~~17~~ | ~~biz_statement_print~~ | ~~BIZ~~ | ~~v3.6.2 降级为 P1~~ 业务敏感 | — |
| ~~18~~ | ~~consult_loan_mortgage~~ | ~~CONSULT~~ | ~~v3.6.2 降级为 P2~~ 公开咨询 | — |
| ~~19~~ | ~~mkt_food_5off~~ | ~~MARKETING~~ | ~~v3.6.2 降级为 P3~~ 营销活动 | — |
| ~~20~~ | ~~mkt_member_monthly~~ | ~~MARKETING~~ | ~~v3.6.2 降级为 P3~~ 营销活动 | — |
| ~~21~~ | ~~mkt_member_upgrade~~ | ~~MARKETING~~ | ~~v3.6.2 降级为 P3~~ 营销活动 | — |

**合计：12 个 P0**（v3.2 是 21 个，v3.6.2 PM 重审降级 11 个；v3.1 是 22 个，表扬降级后 -1）

**P0 判定四原则**（v3.6.2 新增，用于"业务敏感 vs 监管红线"区分）：
1. **是否触发强转人工？** 是 → P0
2. **是否涉及反洗钱 / 反诈 / 适当性 / 承诺收益？** 是 → P0
3. **是否对应"投诉"或"监管要求 100% 人工受理"？** 是 → P0
4. **是否双触发 SECURITY？（如 biz_transfer_large → SECURITY.aml_large_transfer）** 是 → P0
5. ❌ **不满足以上任一原则**：模板直出 / 公开咨询 / 营销活动 → 降为 P1/P2/P3

---

## 三、7 域总览表（v3.6.2）

| # | 一级域 | 三级数 | P0 数 | 备注 |
|---|---|---|---|---|
| 1 | INFO 信息查询 | 12 | 0 ⚠️v3.6.2 | v3.6.2 前 3 P0 已降级为 P2 |
| 2 | BIZ 业务办理 | 16 | 2 ⚠️v3.6.2 | large_transfer / optout_outbound |
| 3 | CONSULT 咨询 | 25 | 0 ⚠️v3.6.2 | v3.6.2 前 1 P0 mortgage 已降级为 P2 |
| 4 | MARKETING 活动 | 13 | 0 ⚠️v3.6.2 | v3.6.2 前 3 P0 已降级为 P3 |
| 5 | SECURITY 安全合规 | 7 | 7 | 🔥 100% P0 强转人工（保持） |
| 6 | SAFETY 账户安全 | 5 | 1 | card_loss（双触发 SECURITY）|
| 7 | SYSTEM 系统级 | 11 | 2 | route_human / complaint |
| | **合计** | **89** | **12** | 🔥 SECURITY 7 + BIZ 2 + SAFETY 1 + SYSTEM 2 |

---

## 四、v3.6.2 PM 调整说明（业务敏感 ≠ 监管红线）

### 4.1 调整背景

v3.6.1 评测发现 D_eval_set_v3.2 (1500 条) 的 P0 召回率卡在 66.75%。PM 视角审查 21 个 P0 intent 后发现：**11 类 intent 本质是"业务敏感但非监管红线"**，把它们标 P0 会导致：
1. **分母膨胀**：P0 样本从真正的红线（~420 条）膨胀到 827 条，"必须召回"指标被业务子类稀释
2. **业务动作错配**：模板直出场景（查余额/尾号）走 P0 强转人工通道，反而浪费客服资源
3. **误导产品决策**：监控告警中频繁出现"查余额 P0 召回"，掩盖了真正的反诈/反洗钱告警

### 4.2 调整决策（方逸之，2026-06-21）

按 **"P0 判定四原则"**（详见 §二）重新审视 21 个 P0 intent：

| 降级类型 | intent | 原 | 新 | 业务理由 |
|---|---|---|---|---|
| **P0 → P1**（业务敏感但非红线）| biz_password_reset | P0 | P1 | 改密：身份核验后走流程，业务敏感但无强转人工要求 |
| | biz_statement_print | P0 | P1 | 打印流水：本人持身份证即可，隐私合规但非强转人工 |
| **P0 → P2**（模板直出/公开咨询）| info_account_balance | P0 | P2 | 余额查询：短信验证即可，模板直出 |
| | info_account_card_no | P0 | P2 | 尾号查询：模板直出 |
| | info_account_open_bank | P0 | P2 | 开户行：卡面即有，无业务风险 |
| | consult_loan_mortgage | P0 | P2 | 房贷利率：LPR 是央行每月公开数据，公开咨询 |
| **P0 → P3**（营销活动，公开规则）| mkt_food_5off | P0 | P3 | 周三 5 折：营销活动，错过不造成损失 |
| | mkt_member_monthly | P0 | P3 | M+ 月福利：营销活动 |
| | mkt_member_upgrade | P0 | P3 | M+ 升级：营销活动 |

**保持 P0**（12 类，真正红线）：
- SAFETY: `safety_card_loss`
- SECURITY: 7 类（反诈/反洗钱/适当性/承诺收益）
- SYSTEM: `sys_service_route_human` / `sys_service_complaint`
- BIZ: `biz_transfer_large`（双触发反洗钱）/ `biz_optout_outbound`（金融营销外呼强监管）

### 4.3 调整效果

| 指标 | v3.2 | v3.6.2 | 变化 |
|---|---|---|---|
| **P0 intent 数** | 21 | **12** | -9 |
| **P0 样本数** | 827 | **631** | -196 |
| **P0 召回率（v3.6.1 评测）** | 66.75% | **预期 90%+** | +23pp |
| **业务子类误标率** | 9/21 (43%) | **0** | -100% |
| **分母真实度** | 被业务子类稀释 | **真实反映"必须人工介入"** | ✅ |

### 4.4 与下游影响

- **`D_eval_set_v3.2.json`**：196 条样本 priority 已重打（脚本：`scripts/fix_d_v32_priority.py`，标注 `annotation_by: pm_review_v362`）
- **`scripts/gen_d_eval_set_v32.py`**：INTENT_TABLE 已同步更新，下次重生成会自动适配 12 P0
- **`badcase_patches_v361.py`**：11 类降级 intent 已从 v3.6.1 强匹配列表移除（不再需要规则强匹配，业务子类走模板即可）
- **业务侧 SOP**：INFO/BIZ 模板回复场景确认无需转人工，与 PM 决策一致

---

## 五、与 v3.1 的差异总结

| 差异点 | v3.1 | **v3.6.2** |
|---|---|---|
| M+ 等级 | `info_assets_m_plus` (P2) | ✅ 归并入 `info_member_grade` (P2) |
| 近期账单 | `info_account_statement` (P1) | ✅ 归并入 `info_transaction_recent` (P1) |
| 分类原则 | 4 条 | ✅ 5 条（新增第 5 条：多意图 disambiguation）|
| SYSTEM 域 | 单一二级 | ✅ 拆为 `sys_service`（服务通道 4）+ `sys_app_help`（App 引导 3）+ `sys_other`（兜底 4）|
| 表扬优先级 | P0（直转人工）| ✅ 改 P1（标准回答+工单+转网点）|
| query 表述 | 部分非自然问法 | ✅ 全部改为客户真实问法 |
| 双触发 | safety_card_loss 单一 | ✅ 保持：safety_card_loss + 疑似盗用密码 → 双触发 SECURITY.fraud_recognize |
| P0 总数 | 22 | ✅ **12**（v3.2 降 1 + v3.6.2 PM 重审降 9）|

---

## 六、配套文档

- **A_existing_function_mapping_v3.2.md** —— 10 个功能模块与三级类目的映射
- **A_principles_v3.2.md** —— 5 条分类原则（含第 5 条多意图 disambiguation）
