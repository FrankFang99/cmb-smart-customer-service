# Badcase 标注池周报 (v3.4.0)

> 生成时间: 2026-06-11T23:25:08

## 概览
- 总数: 13
- 已修复: 1 (7.7%)
- 待修复 P0: 5
- 待修复 P1: 7

## 根因分布
- intent_mismatch: 7
- l0_miss_trigger: 5
- cascade_routing_err: 1

## 修复动作分布
- pending: 9
- add_intent_pattern: 2
- adjust_threshold: 1
- add_faq: 1

## P 等级分布
- P1: 7
- P0: 6

## P0 待办 Top 10
- SMART_00315
- SMART_00317
- SMART_00958
- SMART_00474
- SMART_00303

## P1 待办 Top 10
- SMART_00407
- SMART_00971
- SMART_00264
- SMART_00830
- SMART_00511
- SMART_00986
- SMART_01016

## 详细记录

### SMART_00315 [P0] (待修)
- 问题: 转人工
- 期望意图: `cons_urg_human`
- 实际意图: `cons_urg_human`
- 根因: cascade_routing_err
- 修复: adjust_threshold
- 备注: '转人工' 应 100% 转人工 (cascade L0), 不该走 L2 RAG 模板. 在 cascade 路由中, cons_urg_human 强制 L0 转人工, 不论 intent_conf.

### SMART_00407 [P1] (待修)
- 问题: 申请信用卡
- 期望意图: `cons_prod_credit`
- 实际意图: `sales_credit_prod`
- 根因: intent_mismatch
- 修复: add_intent_pattern
- 备注: 在意图识别规则中, 让 '申请信用卡' / '我想办信用卡' 同时匹配 cons_prod_credit (咨询) 和 sales_credit_prod (营销). 当前规则偏向 sales, 但客户问的多是产品咨询.

### SMART_00971 [P1] (待修)
- 问题: 查一下交易明细
- 期望意图: `info_acc_detail`
- 实际意图: `info_tran_record`
- 根因: intent_mismatch
- 修复: pending
- 备注: -

### SMART_00317 [P0] (待修)
- 问题: 需要人工服务
- 期望意图: `cons_urg_human`
- 实际意图: `cons_urg_human`
- 根因: l0_miss_trigger
- 修复: pending
- 备注: -

### SMART_00264 [P1] (待修)
- 问题: 转账到别的银行
- 期望意图: `biz_tran_external`
- 实际意图: `info_prog_transfer`
- 根因: intent_mismatch
- 修复: add_intent_pattern
- 备注: '转账到别的银行' 包含 '转账' + '别的银行' 应匹配 biz_tran_external. 当前规则把 '别的银行' 当查询走了 info_prog_transfer. 加规则: '别的银行'/'跨行'/'他行' 强匹配 biz_tran_external.

### SMART_00958 [P0] (待修)
- 问题: 账户异常冻结
- 期望意图: `sec_freeze_unexpected`
- 实际意图: `sec_freeze_unexpected`
- 根因: l0_miss_trigger
- 修复: pending
- 备注: -

### SMART_00830 [P1] (待修)
- 问题: 办什么卡好
- 期望意图: `sales_credit_prod`
- 实际意图: `sys_invalid`
- 根因: intent_mismatch
- 修复: pending
- 备注: -

### SMART_00511 [P1] (待修)
- 问题: 有什么好理财
- 期望意图: `cons_prod_wealth`
- 实际意图: `sales_wealth_prod`
- 根因: intent_mismatch
- 修复: pending
- 备注: -

### SMART_00986 [P1] (待修)
- 问题: 查一下交易明细
- 期望意图: `info_acc_detail`
- 实际意图: `info_tran_record`
- 根因: intent_mismatch
- 修复: pending
- 备注: -

### SMART_00474 [P0] (待修)
- 问题: 收到陌生消费
- 期望意图: `sec_stolen_card`
- 实际意图: `sec_stolen_card`
- 根因: l0_miss_trigger
- 修复: pending
- 备注: -

### SMART_01016 [P1] (待修)
- 问题: 转钱到招行卡
- 期望意图: `biz_tran_internal`
- 实际意图: `sys_invalid`
- 根因: intent_mismatch
- 修复: pending
- 备注: -

### SMART_00680 [P0] (已修复)
- 问题: 被诈骗了
- 期望意图: `cons_urg_loss`
- 实际意图: `sec_fraud_report`
- 根因: l0_miss_trigger
- 修复: add_faq
- 备注: '被诈骗了' 应触发 L0 反诈骗红线 + 100% 转人工 + 提示 '请立即挂失 + 报警 110'. 实际走了 sec_fraud_report 模板, 未强转人工, 不符合银行业 P0 红线.

### SMART_00303 [P0] (待修)
- 问题: 转人工
- 期望意图: `cons_urg_human`
- 实际意图: `cons_urg_human`
- 根因: l0_miss_trigger
- 修复: pending
- 备注: -
