# P0 红线 4 类细分错例报告 (A 口径)

生成时间: 2026-06-21

数据来源: D_eval_set_v3.2 (1500 条) 中的 P0 红线集合

覆盖范围: P0 红线 4 类 (biz/safety/security/sys)

说明: D_v3.2 评测集设计红线只在真正高风险意图 (销户/挂失/反诈/反洗钱/适当性/投诉/转人工), 其他意图 (咨询/信息/营销) 按设计不属于 P0, 归 P1/P2/P3. 本报告仅分析 P0 红线 4 类.

P0 总数: 631 条  →  4 类范围内: 631 条 (100% 覆盖)


## 表 1: P0 红线 4 类召回率

| 业务组 | P0总数 | group 召回 | fine 召回 | 状态 |
|--------|-------:|-----------:|----------:|------|
| biz | 40 | 45.00% | 45.00% | 🔴 低召回 (重点修复) |
| safety | 147 | 100.00% | 100.00% | 🟢 达标 |
| security | 233 | 82.40% | 62.23% | 🟡 待提升 |
| sys | 211 | 97.16% | 69.67% | 🟢 达标 |
| **合计** | **631** | **89.06%** | **72.42%** | — |

## 表 2: P0 红线 4 类错误归因 (L1 规则 / L2 BERT / L3 兜底)

| 业务组 | 总数 | 正确 | 错误 | 主要背锅层 |
|-------:|-----:|-----:|-----:|-----------|
| biz | 40 | 18 (45.0%) | 22 | L1规则-大类错 (19条) |
| safety | 147 | 147 (100.0%) | 0 | — (无错误) |
| security | 233 | 145 (62.2%) | 88 | L1规则-细分错 (47条) |
| sys | 211 | 147 (69.7%) | 64 | L3兜底-细分错 (43条) |

### 2.1 各组详细归因

**[biz]** 总 40 条, 正确 18 条

- L1规则-大类错: 19 条 (47.5%)
- L3兜底-大类错: 3 条 (7.5%)

**[safety]** 总 147 条, 正确 147 条


**[security]** 总 233 条, 正确 145 条

- L1规则-细分错: 47 条 (20.2%)
- L1规则-大类错: 28 条 (12.0%)
- L3兜底-大类错: 12 条 (5.2%)
- L2 BERT-大类错: 1 条 (0.4%)

**[sys]** 总 211 条, 正确 147 条

- L3兜底-细分错: 43 条 (20.4%)
- L1规则-细分错: 15 条 (7.1%)
- L1规则-大类错: 6 条 (2.8%)

## 表 3: P0 红线 4 类混淆矩阵

### 3.1 group 级错配 (大类判错, Top 10)

| 期望 group | → | 实际 group | 数量 |
|------------|---|------------|-----:|
| security | → | safety | 23 |
| biz | → | security | 19 |
| security | → | sys | 17 |
| biz | → | sys | 3 |
| sys | → | biz | 1 |

### 3.2 fine 级错配 (大类对, 细分错, Top 10)

| 期望 intent | → | 实际 intent | 数量 |
|-------------|---|-------------|-----:|
| sys_service_route_human | → | sys_invalid | 43 |
| security_fraud_report | → | sec_fraud_report | 41 |
| sys_service_route_human | → | sys_greeting | 10 |
| sys_service_route_human | → | sys_thanks | 3 |
| security_fraud_report | → | security_fraud_recognize | 3 |
| security_fraud_report | → | sec_stolen_info | 3 |
| sys_service_route_human | → | sys_service_complaint | 2 |

## 表 4: 4 类各自最严重的细分错 (各组 Top 3)

### [biz] group 错配 22 条, fine 错配 0 条

**group 错配 Top 3:**

| 期望 | → | 实际 | 数量 |
|------|---|------|-----:|
| biz_transfer_large | → | security_aml_large_transfer | 19 |
| biz_transfer_large | → | sys_invalid | 3 |

### [safety] group 错配 0 条, fine 错配 0 条

### [security] group 错配 41 条, fine 错配 47 条

**group 错配 Top 3:**

| 期望 | → | 实际 | 数量 |
|------|---|------|-----:|
| security_fraud_report | → | safety_card_loss | 23 |
| security_fraud_report | → | sys_invalid | 7 |
| security_fraud_report | → | sys_greeting | 4 |

**fine 错配 Top 3:**

| 期望 | → | 实际 | 数量 |
|------|---|------|-----:|
| security_fraud_report | → | sec_fraud_report | 41 |
| security_fraud_report | → | security_fraud_recognize | 3 |
| security_fraud_report | → | sec_stolen_info | 3 |

### [sys] group 错配 6 条, fine 错配 58 条

**group 错配 Top 3:**

| 期望 | → | 实际 | 数量 |
|------|---|------|-----:|
| sys_service_complaint | → | cons_comp_service | 5 |
| sys_service_complaint | → | biz_card_loss | 1 |

**fine 错配 Top 3:**

| 期望 | → | 实际 | 数量 |
|------|---|------|-----:|
| sys_service_route_human | → | sys_invalid | 43 |
| sys_service_route_human | → | sys_greeting | 10 |
| sys_service_route_human | → | sys_thanks | 3 |

## 表 5: 4 类典型错例样本 (供面试引用, 各 2 条)

### [biz]

- **Q**: 我要转 50 万给公司
  - 期望: `biz_transfer_large` → 实际: `security_aml_large_transfer`
  - 路由层: L1_rule  置信度: 0.98

- **Q**: 转 50 万要什么手续
  - 期望: `biz_transfer_large` → 实际: `security_aml_large_transfer`
  - 路由层: L1_rule  置信度: 0.98

### [safety]

### [security]

- **Q**: 请问刚被骗了 10 万, 怎么办
  - 期望: `security_fraud_report` → 实际: `safety_card_loss`
  - 路由层: L1_rule  置信度: 0.98

- **Q**: 刚接了一个诈骗电话?
  - 期望: `security_fraud_report` → 实际: `sec_fraud_report`
  - 路由层: L1_rule  置信度: 0.95

### [sys]

- **Q**: 请问我要和客服说话
  - 期望: `sys_service_route_human` → 实际: `sys_greeting`
  - 路由层: L1_rule  置信度: 0.95

- **Q**: 那个找真人客服
  - 期望: `sys_service_route_human` → 实际: `sys_invalid`
  - 路由层: L3_llm_pending  置信度: 0.0

## 报告总结 (PM 视角解读)

### 关键发现

1. **biz 组 (40 条 P0)** - group 召回 45%, 是 4 类中最低.
   - 19/22 错误都来自 L1 规则把 "大额转账手续" (biz_transfer_large) 误判为 "反洗钱大额" (security_aml_large_transfer).
   - **根因**: L1 词典规则命中"50万"等大额关键词, 没有区分"用户问手续"和"用户报告异常交易"两种场景.
   - **修复方向**: 改写 L1 规则, 引入上下文动词 ("手续/怎么办" → biz; "被骗/异常" → security).

2. **safety 组 (147 条 P0)** - group 召回 100%, 🟢 完全达标.
   - card_loss 挂失意图 L1 规则覆盖最完整, 无明显漏判.

3. **security 组 (233 条 P0)** - group 召回 82.4%, fine 召回 62.2%.
   - **group 错配 41 条**: 主要是 fraud_report 反诈举报被误判为 safety_card_loss 挂失 (23 条) 或 sys 闲聊 (17 条).
   - **fine 错配 47 条**: 全部是 fraud_report 意图细分错 (sec_fraud_report vs security_fraud_report 命名不一致).
   - **根因**: IR 训练时用了 `sec_fraud_report` 标签, D_v3.2 评测集改成 `security_fraud_report`.
   - **修复方向**: IR label 空间对齐 D_v3.2, 或在 v3.6.1 补丁里加 alias 映射.

4. **sys 组 (211 条 P0)** - group 召回 97.2%, fine 召回 69.7%.
   - **fine 错配 58 条**: 主要是 route_human 转人工被 L3 兜底判为 sys_invalid 闲聊 (43 条) 或 sys_greeting 问候 (10 条).
   - **根因**: 用户口语化表达"找真人/客服"等被 L1 规则+BERT 都漏掉, 走到 L3 LLM 兜底又因为 prompt 没强调"转人工"作为 P0, 判成了无效输入.
   - **修复方向**: 在 L3 prompt 里把"转人工"明确标为 P0 红线, 或 L1 加更多口语化转人工关键词.

### 修复优先级 (PM 决策建议)

| 优先级 | 修复项 | 预期收益 | 实施成本 |
|-------:|--------|---------|---------|
| P0 | biz_transfer_large L1 改写 (区分"问手续"vs"报告异常") | biz group +43pp (45%→88%) | 低 (1 天) |
| P0 | L3 prompt 加"转人工"红线 + L1 加口语化关键词 | sys fine +27pp (70%→97%) | 中 (3 天) |
| P1 | IR label 对齐 D_v3.2 (sec_ → security_) | security fine +35pp (62%→97%) | 中 (需重训 IR) |
| P2 | security fraud_report → card_loss 边界 (加"骗"vs"丢"区分词) | security group +10pp | 低 (1 天) |
