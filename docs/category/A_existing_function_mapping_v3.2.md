# 现有功能模块与三级类目映射 v3.2

> 文档目的：将招行 App / 网银 / 客服系统的 **10 个现有功能模块** 映射到 v3.2 终版三级类目，作为意图识别（NLU）→ 业务路由（Router）→ 功能对接（API）的桥梁。
>
> 适用版本：v3.2

---

## 一、10 个功能模块总览

| # | 模块 | 模块 ID | 涵盖三级数 | 涵盖 P0 数 | 数据源 |
|---|---|---|---|---|---|
| 1 | 账户信息查询 | `mod_account_info` | 6 | 3 | 账户系统 / 交易系统 |
| 2 | 信用卡服务 | `mod_credit_card` | 8 | 0 | 信用卡系统 |
| 3 | 借记卡业务办理 | `mod_debit_card` | 6 | 2 | 借记卡系统 |
| 4 | 贷款服务 | `mod_loan` | 4 | 1 | 贷款系统 |
| 5 | 财富管理 | `mod_wealth` | 7 | 1 | 理财系统 / 基金系统 / 黄金系统 |
| 6 | 支付与转账 | `mod_payment` | 5 | 2 | 支付系统 / 反洗钱系统 |
| 7 | 外汇与跨境 | `mod_fx` | 4 | 1 | 外汇系统 |
| 8 | 营销活动 | `mod_marketing` | 11 | 3 | 营销系统 / 活动配置 |
| 9 | 会员与积分 | `mod_member` | 5 | 2 | 会员系统 |
| 10 | 系统与客服 | `mod_system` | 11 | 2 | 工单系统 / 客服系统 / 兜底话术 |
| | **合计** | — | **67** | **17** | |

> **注意**：67 ≠ 84，因为部分三级类目被多个模块共享（如 `biz_password_reset` 跨 mod_debit_card 和 mod_credit_card）。

---

## 二、模块详细映射

### 模块 1：账户信息查询 `mod_account_info`（6 个三级）

| 涉及三级 | 优先级 | 数据源 API | 备注 |
|---|---|---|---|
| info_account_balance | P0 | `/api/account/balance` | 仅展示，不动账 |
| info_account_card_no | P0 | `/api/account/card-no` | 脱敏展示 |
| info_account_open_bank | P0 | `/api/account/open-bank` | 开户行信息 |
| info_account_type | P1 | `/api/account/type` | 一类/二类/三类户 |
| info_transaction_recent | P1 | `/api/transaction/recent` | 🔥 v3.2 归并：含原 statement |
| info_transaction_filter | P2 | `/api/transaction/filter` | 按时间/类型筛选 |

> 🔥 **v3.2 变更**：删除 `info_account_statement`（已归并入 `info_transaction_recent`）

---

### 模块 2：信用卡服务 `mod_credit_card`（8 个三级）

| 涉及三级 | 优先级 | 数据源 API | 备注 |
|---|---|---|---|
| info_credit_limit | P1 | `/api/credit/limit` | 总额度/可用额度 |
| info_credit_bill | P1 | `/api/credit/bill` | 本期账单金额 |
| info_credit_point | P2 | `/api/credit/point` | 信用卡积分余额 |
| biz_credit_card_apply | P1 | `/api/credit/apply` | 信用卡申请 |
| biz_credit_card_billing_date | P1 | `/api/credit/billing-date` | 改账单日 |
| consult_credit_card_bill | P1 | KB | 账单日规则说明 |
| consult_credit_card_fee | P1 | KB | 年费规则 |
| consult_credit_card_limit | P1 | KB | 提额条件说明 |
| consult_credit_card_product | P2 | KB | 卡种对比 |
| consult_credit_card_installment | P2 | KB | 分期手续费 |

> 🔥 **多意图 disambiguation**：
> - `consult_credit_card_limit` "信用卡额度怎么提" → 答完问"是查询提额条件，还是要现在申请？" + `/api/credit/apply` 入口

---

### 模块 3：借记卡业务办理 `mod_debit_card`（6 个三级）

| 涉及三级 | 优先级 | 数据源 API | 备注 |
|---|---|---|---|
| biz_password_reset | P0 | `/api/debit/password-reset` | 🔥 强合规，模板回复 |
| biz_password_change | P1 | `/api/debit/password-change` | 改密码（已知原密码）|
| biz_card_apply | P1 | `/api/debit/apply` | 新办借记卡 |
| biz_card_activate | P1 | `/api/debit/activate` | 新卡激活 |
| biz_card_replace | P1 | `/api/debit/replace` | 损坏换卡 |
| biz_statement_print | P0 | `/api/debit/statement` | 🔥 隐私合规，模板回复 |

> 🔥 **密码分流（原则 4）**：
> - `biz_password_reset` ← 主动办（"我要改密码"）
> - `safety_password_forget` ← SAFETY 异常态（"我密码忘了"）
> - `safety_password_locked` ← SAFETY 异常态（"我密码被锁了"）
> - 双触发：疑似盗用 → SAFETY + SECURITY

---

### 模块 4：贷款服务 `mod_loan`（4 个三级）

| 涉及三级 | 优先级 | 数据源 API | 备注 |
|---|---|---|---|
| consult_loan_mortgage | P0 | KB | 🔥 利率敏感 |
| consult_loan_credit | P1 | KB | 信用贷利率 |
| consult_loan_business | P2 | KB | 小微贷条件 |
| consult_loan_repay_method | P1 | KB | 等额本息 vs 本金 |
| biz_loan_apply | P1 | `/api/loan/apply` | 贷款申请 |
| biz_loan_repay | P1 | `/api/loan/repay` | 提前还款 |

> 🔥 **多意图 disambiguation**：
> - "贷款进度" → 答完问"是查询进度，还是催办？" + 查询/催办入口

---

### 模块 5：财富管理 `mod_wealth`（7 个三级）

| 涉及三级 | 优先级 | 数据源 API | 备注 |
|---|---|---|---|
| biz_wealth_buy | P1 | `/api/wealth/buy` | 理财购买 |
| consult_wealth_deposit | P1 | KB | 大额存单 |
| consult_wealth_fund | P1 | KB | 基金风险等级 |
| consult_wealth_insurance | P1 | KB | 保险犹豫期 |
| consult_wealth_gold | P2 | KB | 纸黄金 |
| security_suitability_unrated | P0 | 适当性系统 | 🔥 拦截 + 引导评估 |
| security_suitability_mismatch | P0 | 适当性系统 | 🔥 拦截 + 人工 |
| security_promise_yield | P0 | 监管系统 | 🔥 承诺收益拦截 |

> 🔥 **P0 联动**：购买/咨询理财时，若触发 SECURITY 三个三级之一，**100% 强转人工**

---

### 模块 6：支付与转账 `mod_payment`（5 个三级）

| 涉及三级 | 优先级 | 数据源 API | 备注 |
|---|---|---|---|
| biz_transfer_same_bank | P1 | `/api/payment/transfer-same` | 行内转账 |
| biz_transfer_cross_bank | P1 | `/api/payment/transfer-cross` | 跨行转账 |
| **biz_transfer_large** | **P0** | `/api/payment/transfer-large` | 🔥 **双触发 SECURITY.aml_large_transfer** |
| consult_fee_transfer | P1 | KB | 转账手续费 |
| consult_fee_account | P1 | KB | 账户管理费 |

> 🔥 **大额反洗钱联动**：`biz_transfer_large` 触发后**同时激活** `security_aml_large_transfer`，反洗钱系统+人工审核双通道
>
> 🔥 **多意图 disambiguation**：
> - "跨行转账怎么操作" → 答完问"是想要现在办跨行转账吗？" + `/api/payment/transfer-cross` 入口

---

### 模块 7：外汇与跨境 `mod_fx`（4 个三级）

| 涉及三级 | 优先级 | 数据源 API | 备注 |
|---|---|---|---|
| consult_fx_rate | P1 | `/api/fx/rate` | 实时汇率 |
| consult_fx_cross | P2 | KB | 跨境汇款限额 |
| consult_fee_cross_border | P2 | KB | 境外汇款手续费 |
| security_aml_cross_border | P0 | 反洗钱系统 | 🔥 强转人工 + 人工审核 |

> 🔥 **P0 联动**：跨境汇款触发 `security_aml_cross_border`，**100% 强转人工**

---

### 模块 8：营销活动 `mod_marketing`（11 个三级）

| 涉及三级 | 优先级 | 数据源 API | 备注 |
|---|---|---|---|
| mkt_food_5off | P0 | `/api/mkt/food-5off` | 🔥 每周规则易变 |
| mkt_food_brand | P1 | `/api/mkt/food-brand` | 品牌优惠 |
| mkt_cinema_99 | P1 | `/api/mkt/cinema-99` | 影票 9 块 9 |
| mkt_pay_firstbind | P1 | `/api/mkt/firstbind` | 首绑立减 |
| mkt_pay_cashback | P1 | `/api/mkt/cashback` | 支付满减 |
| mkt_pay_coupon | P2 | `/api/mkt/coupon` | 加息券 |
| mkt_invite_cash | P2 | `/api/mkt/invite` | 邀请好友 |
| mkt_signin_daily | P2 | `/api/mkt/signin` | 签到 |
| mkt_point_double | P2 | `/api/mkt/point-double` | 积分翻倍日 |
| mkt_newuser_gift | P1 | `/api/mkt/newuser` | 新户首绑礼 |
| mkt_birthday_priv | P2 | `/api/mkt/birthday` | 生日特权 |
| **mkt_member_monthly** | **P0** | `/api/mkt/member-monthly` | 🔥 每月变 |
| **mkt_member_upgrade** | **P0** | `/api/mkt/member-upgrade` | 🔥 活动期 |

> **P0 MARKETING（3 个）**：5off / member_monthly / member_upgrade
> 🔥 **临时 vs 常驻判断**：活动规则 → MARKETING；产品规则（利率/费率）→ CONSULT

---

### 模块 9：会员与积分 `mod_member`（5 个三级）

| 涉及三级 | 优先级 | 数据源 API | 备注 |
|---|---|---|---|
| **info_member_grade** | P2 | `/api/member/grade` | 🔥 v3.2 归并：含原 m_plus |
| info_member_point | P2 | `/api/member/point` | 积分余额 |
| consult_member_m_plus | P1 | KB | M+ 升级规则 |
| consult_member_point | P2 | KB | 积分使用规则 |
| mkt_member_monthly | P0 | `/api/mkt/member-monthly` | 🔥 跨模块：营销系统 |
| mkt_member_upgrade | P0 | `/api/mkt/member-upgrade` | 🔥 跨模块：营销系统 |

> 🔥 **v3.2 归并说明**：
> - 删除 `info_assets_m_plus`（M+ 等级 = 招行会员等级，归 `info_member_grade`）
> - `mkt_member_*` 同时被 mod_member 和 mod_marketing 引用

---

### 模块 10：系统与客服 `mod_system`（11 个三级）

#### 10.1 sys_service 服务通道（4 个三级）

| 涉及三级 | 优先级 | 对接系统 | 备注 |
|---|---|---|---|
| **sys_service_route_human** | **P0** | 在线客服 | 直转 |
| **sys_service_complaint** | **P0** | 工单系统 + 客服 | 🔥 监管 100% 人工受理 |
| sys_service_praise | P1 | 工单系统 + 网点 | 🔥 v3.2 改 P1：模板回答+工单+转网点 |
| sys_service_feedback | P1 | 工单系统 | 收集 + 工单 |

#### 10.2 sys_app_help App 使用引导（3 个三级）

| 涉及三级 | 优先级 | 对接系统 | 备注 |
|---|---|---|---|
| sys_app_help_navigation | P1 | KB | "理财在哪" |
| sys_app_help_setting | P1 | KB | "怎么改默认卡" |
| sys_app_help_data | P2 | KB | "怎么导出对账单" |

#### 10.3 sys_other 系统兜底（4 个三级）

| 涉及三级 | 优先级 | 对接系统 | 备注 |
|---|---|---|---|
| sys_other_greet | P3 | 兜底话术 | "你好" |
| sys_other_invalid | P3 | 兜底话术 | 乱码 |
| sys_other_farewell | P3 | 兜底话术 | "谢谢" |
| sys_other_unclear | P3 | disambiguation | 🔥 多种意图无法判定时，按原则 5 处理 |

> 🔥 **v3.2 拆分说明**：
> - **服务通道**（投诉/表扬/反馈/转人工）= 客服工单系统
> - **App 引导** = 知识库引导
> - **系统兜底** = 闲聊/无效/多意图模糊

---

## 三、跨模块联动清单（v3.2 关键）

| 触发三级 | 联动三级 | 联动系统 | 业务含义 |
|---|---|---|---|
| `biz_transfer_large` | `security_aml_large_transfer` | 反洗钱系统 | 🔥 大额转账必触发反洗钱审核 |
| `safety_card_loss` | `security_fraud_recognize` | 反诈中心 + 95555 | 🔥 挂失必联动反诈核实 |
| `safety_password_forget` (疑似盗用) | `security_fraud_recognize` | 反诈中心 | 🔥 密码疑似被盗→反诈 |
| `biz_wealth_buy` (R1 买 R4) | `security_suitability_mismatch` | 适当性系统 | 🔥 适当性不匹配拦截 |
| `consult_wealth_*` 任何 | `security_promise_yield` (若 query 含"保本/保证") | 监管系统 | 🔥 承诺收益拦截 |
| `biz_transfer_cross_border` | `security_aml_cross_border` | 反洗钱系统 | 🔥 跨境必触发反洗钱 |
| `biz_optout_outbound` | 工单系统 | 投诉受理 | 🔥 监管要求记录 |
| `sys_service_complaint` | 工单系统 + 客服 | 投诉工单带会话 | 🔥 监管 100% 人工 |

---

## 四、模块对接优先级（开发排期建议）

| 优先级 | 模块 | 原因 |
|---|---|---|
| P0-1 | mod_system（含 7 个 P0）| 投诉/转人工/P0 兜底是客服系统最基本能力 |
| P0-2 | mod_payment（含 2 个 P0）| 大额反洗钱 + 转账是高频 + 合规要求 |
| P0-3 | mod_wealth（含 3 个 P0）| 适当性 + 承诺收益是监管红线 |
| P0-4 | mod_debit_card（含 2 个 P0）| 密码合规 + 流水合规 |
| P1 | mod_account_info | 高频查询 |
| P1 | mod_credit_card | 高频查询 |
| P1 | mod_marketing | 活动配置灵活 |
| P2 | mod_loan | 低频 |
| P2 | mod_fx | 低频 |
| P2 | mod_member | 低频 |

---

## 五、配套文档

- **A_standard_v3.2.md** —— 7 域 84 三级全表 + 21 P0 红线
- **A_principles_v3.2.md** —— 5 条分类原则
