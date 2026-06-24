# Loop Engineering v3.7.4 报告

**运行时间**: 2026-06-22T13:23:47.259435  
**基线版本**: v3.7.0-e2e  
**数据集**: D v3.2 (1500 条)

## 一、基线指标（v3.7.0）

| 维度 | 数值 |
|---|---|
| 路由正确率 | 91.20% |
| P0 转人工率 | 98.26% |
| 幻觉率 | 0.00% |
| 澄清率 | 5.73% |
| 平均延迟 | 8.0ms |

## 二、Badcase 聚类（按 expected_action）

共发现 12 个失败聚类，总 miss 72 条：

| 严重度 | 意图 | miss/total | 准确率 |
|---|---|---|---|
| P0 | card_freeze | 25/96 | 73.96% |
| P2 | loan_repay | 8/35 | 77.14% |
| P2 | show_balance | 7/28 | 75.00% |
| P2 | consult_credit_card_pick | 6/53 | 88.68% |
| P2 | consult_credit_loan | 5/38 | 86.84% |
| P2 | fraud_recognize | 5/22 | 77.27% |
| P2 | consult_installment | 5/20 | 75.00% |
| P2 | card_activate | 3/40 | 92.50% |
| P2 | consult_fund_risk | 3/40 | 92.50% |
| P2 | route_human | 2/152 | 98.68% |
| P2 | fraud_report | 2/107 | 98.13% |
| P2 | aml_cross_border | 1/19 | 94.74% |

## 三、Patch 候选

### [P0] card_freeze
- **诊断**: 账户冻结类 query 走 RAG_KB/CASCADE_TEMPLATE 而非 L0_HUMAN
- **Patch 类型**: `L0_keyword_extension`
- **Patch 建议**: 在 L0 红线词典增加卡冻结口语化变体（卡被锁了 / 卡片锁了 / 不能用卡了）
- **预期改进**: miss 25 → ~3（参考招行口语化扩展经验）

### [P2] loan_repay
- **诊断**: 未知失败模式，accuracy=0.7714, miss=8
- **Patch 类型**: `manual_analysis_required`
- **Patch 建议**: 需拉取该意图的错分 case 样本做人工根因分析
- **预期改进**: TBD（依赖人工分析结果）

### [P2] show_balance
- **诊断**: 未知失败模式，accuracy=0.75, miss=7
- **Patch 类型**: `manual_analysis_required`
- **Patch 建议**: 需拉取该意图的错分 case 样本做人工根因分析
- **预期改进**: TBD（依赖人工分析结果）

### [P2] consult_credit_card_pick
- **诊断**: 信用卡办理类 query 路径正确但 sub-intent 错（普通卡 vs 学生卡 vs 白金卡）
- **Patch 类型**: `slot_clarification`
- **Patch 建议**: 在 IntentRecognizer 增加卡类型上下文槽位追问逻辑
- **预期改进**: miss 6 → ~2（槽位澄清）

### [P2] consult_credit_loan
- **诊断**: 未知失败模式，accuracy=0.8684, miss=5
- **Patch 类型**: `manual_analysis_required`
- **Patch 建议**: 需拉取该意图的错分 case 样本做人工根因分析
- **预期改进**: TBD（依赖人工分析结果）

### [P2] fraud_recognize
- **诊断**: 未知失败模式，accuracy=0.7727, miss=5
- **Patch 类型**: `manual_analysis_required`
- **Patch 建议**: 需拉取该意图的错分 case 样本做人工根因分析
- **预期改进**: TBD（依赖人工分析结果）

### [P2] consult_installment
- **诊断**: 未知失败模式，accuracy=0.75, miss=5
- **Patch 类型**: `manual_analysis_required`
- **Patch 建议**: 需拉取该意图的错分 case 样本做人工根因分析
- **预期改进**: TBD（依赖人工分析结果）

### [P2] card_activate
- **诊断**: 未知失败模式，accuracy=0.925, miss=3
- **Patch 类型**: `manual_analysis_required`
- **Patch 建议**: 需拉取该意图的错分 case 样本做人工根因分析
- **预期改进**: TBD（依赖人工分析结果）

### [P2] consult_fund_risk
- **诊断**: 未知失败模式，accuracy=0.925, miss=3
- **Patch 类型**: `manual_analysis_required`
- **Patch 建议**: 需拉取该意图的错分 case 样本做人工根因分析
- **预期改进**: TBD（依赖人工分析结果）

### [P2] route_human
- **诊断**: 未知失败模式，accuracy=0.9868, miss=2
- **Patch 类型**: `manual_analysis_required`
- **Patch 建议**: 需拉取该意图的错分 case 样本做人工根因分析
- **预期改进**: TBD（依赖人工分析结果）

### [P2] fraud_report
- **诊断**: 未知失败模式，accuracy=0.9813, miss=2
- **Patch 类型**: `manual_analysis_required`
- **Patch 建议**: 需拉取该意图的错分 case 样本做人工根因分析
- **预期改进**: TBD（依赖人工分析结果）

### [P2] aml_cross_border
- **诊断**: 未知失败模式，accuracy=0.9474, miss=1
- **Patch 类型**: `manual_analysis_required`
- **Patch 建议**: 需拉取该意图的错分 case 样本做人工根因分析
- **预期改进**: TBD（依赖人工分析结果）

## 四、预测 v3.7.4 指标 + 回归门控

| 维度 | 基线 (v3.7.0) | 预测 (v3.7.4) | Δ | 底线 |
|---|---|---|---|---|
| P0 转人工率 | 98.26% | 99.15% | +0.89pp | ≥ 95% |
| 路由正确率 | 91.20% | 93.00% | +1.80pp | ≥ 85% |
| 幻觉率 | 0.00% | 0.00% | +0.00pp | ≤ 5% |
| 澄清率 | 5.73% | 8.00% | +2.27pp | ≤ 20% |

**门控结果**: ✅ PASS

## 五、下一步行动

> 应用 P0 patch（card_freeze L0 扩展 + slot 澄清），重跑 D v3.2 验证真实指标，确认通过门控后发版 v3.7.4

---

**Loop Engineering 价值**：把 v3.6.4 之前「业务专家看 badcase → 写 patch → 跑评测」的人工循环，自动化为「badcase 聚类 → patch 候选 → 回归门控」。PM 不需要逐条看 300 个 badcase，只需要看 1 个 P0 聚类 + 审 12 个 patch 候选。回归门控保证每次改动不会引入新 bug，所有改动可追溯。