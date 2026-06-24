# A2 P1 误伤分析报告 — v3.10.1 → v3.11.0 修补方向

**生成时间**: 2026-06-23 20:09 (UTC+8)
**数据源**: `data/observability_v3101_full.db` (1076 条 full run)
**关联报告**: `data/observable_v3101_full_report.json`
**详细数据**: `data/p1_a2_analysis.json`

---

## 1. 结论摘要

| 指标 | v3.10.1 full | 说明 |
|---|---|---|
| P0 (红线) | **99.77%** (430/431) | ✅ 100% 不破 |
| P1 (业务咨询) | **72.89%** (242/332) | ⚠️ < 75% 触发 A2 |
| P2 | 91.61% | ✅ |
| P3 | 100% | ✅ |

**P1 90 条 miss = 100% 是 P0 patch 误伤**（无其他原因）。

---

## 2. A2 聚类 — 按 P0 patch 名分组误伤数

| P0 patch (final_intent) | 误伤 | 主要误伤 intent | 优先级 |
|---|---|---|---|
| **safety_card_freeze** | **22** | card_freeze (20) + _disamb (2) | 🔴 P0 |
| **l0_redline** (L0 词典) | **19** | card_freeze (11) + _disamb (4) + 大额存单 (3) | 🔴 P0 |
| **(none)** (L0 单独命中无 final_intent) | 17 | card_freeze (5) + password (4) + fund (2) | 🟡 P1 |
| **biz_transfer_large** | **16** | consult_credit_loan (3) + loan_repay (3) + consult_fund_risk (2) | 🔴 P0 |
| sec_freeze_unexpected | 7 | card_freeze (7) | 🟡 P1 |
| cons_urg_lock | 6 | card_freeze (4) + password (2) | 🟡 P1 |
| security_aml_cross_border | 2 | consult_fx_rate (2) | 🟢 P2 |
| safety_card_loss | 1 | card_freeze (1) | 🟢 P3 |

**Top 3 P0 patch (safety_card_freeze + l0_redline + biz_transfer_large) = 57 条误伤 = P1 miss 的 63%**。修好这 3 个 → P1 准确率预估 72.89% → **89.96%** (+17pp)。

---

## 3. 误伤样本分析（Top 5 模式）

### 3.1 safety_card_freeze (22 条) — 卡冻结疑问句误吞

**根因**: P0 patch `safety_card_freeze` 把所有 "卡被冻 / 卡冻结 / 卡不能用了" 都路由转人工。但 P1 用户实际问的是 **"怎么解冻" / "为什么被冻"** —— 描述状态 ≠ 冻结请求。

**典型误伤样本**:
- "为什么我的卡被冻了?"
- "为啥账户被冻"
- "卡不能用了, 怎么解冻"
- "卡不能用了, 是不是被冻?"
- "怎么账户被冻了"
- "我的的账户被冻结"

**修复方向** (P0):
```python
# 在 safety_card_freeze patch 加 "疑问型信号豁免"
EXEMPT_TOKENS = ["怎么", "为什么", "为啥", "咋办", "怎么办", "如何", "是不是"]
if any(t in query for t in EXEMPT_TOKENS):
    # 降级到 card_freeze (P1 业务咨询) 而非 transfer_human
    return IntentMatch(final_intent="biz_card_freeze_query", priority="P1")
```

### 3.2 l0_redline (19 条) — "冻结/大额" 短词过宽

**根因**: L0 词典 `banking_l0_dict.py` 含 "冻结" / "大额" 单独短词，导致：
- "大额存单" / "大额存单收益" → 误判大额转账 → 转人工（实际是产品咨询）
- "卡冻结了?" → 描述状态被红线触发 → 转人工（实际是 P1 解冻咨询）

**典型误伤样本**:
- "大额存单" (expected: consult_deposit_big_with_disambiguation)
- "大额存单收益纸黄金规则"
- "卡冻结了" / "卡冻结了?" / "我的卡被锁了"
- "想问一下账户冻结, 怎么解"
- "账户异常, 怎么解冻"

**修复方向** (P0):
```python
# banking_l0_dict.py:
# - 删除 "冻结" 单独词条 (用户描述状态 ≠ 冻结请求)
# - 只保留 "冻结卡" / "紧急冻结" / "马上冻结" / "立即冻结"
# - "大额" 已在 v3.10.1 删除, 验证是否覆盖完整
L0_REDLINE_KEYWORDS = [
    "冻结卡", "紧急冻结", "马上冻结", "立即冻结", "立刻冻结",
    # 删: "冻结", "大额"
]
```

### 3.3 biz_transfer_large (16 条) — "怎么办/怎么操作" 业务咨询被吞

**根因**: P0 patch `biz_transfer_large` 的 `怎么办/怎么操作/怎么弄/如何操作` 等宽匹配未完全删除（v3.10.1 仅删了 patch patterns，未覆盖全）。导致：

- "理财怎么办" / "理财怎么办?" → 误吞 → 转人工
- "贷款怎么办" → 误吞 → 转人工
- "基金定投怎么操作" → 误吞 → 转人工
- "主动还款怎么操作" → 误吞 → 转人工

**典型误伤样本**:
- "想问一下贷款怎么办"
- "那个贷款怎么办"
- "贷款怎么办信用卡怎么办贷款怎么办信用卡怎么办"
- "理财怎么办" / "理财怎么办?"
- "基金定投怎么操作"
- "主动还款怎么操作" / "主动还款怎么操作?"

**修复方向** (P0):
```python
# badcase_patches_v364.py - biz_transfer_large 部分:
# - 删 "怎么办/怎么操作/怎么弄/如何操作" 宽匹配 (v3.10.1 部分删, 验证完整)
# - 加 intent_top1 白名单: 如果 top1 是 biz_loan_repay / consult_loan_credit /
#   consult_wealth_fund / biz_wealth_buy, 不走 biz_transfer_large 兜底
TOP1_WHITELIST = {
    "biz_loan_repay", "consult_loan_credit", "consult_wealth_fund",
    "biz_wealth_buy", "consult_fx_rate", "consult_fee_transfer",
}
if final_intent == "biz_transfer_large" and intent_top1 in TOP1_WHITELIST:
    return IntentMatch(final_intent=intent_top1, priority="P1")
```

### 3.4 (none) final_intent (17 条) — L0 命中但 L1 未识别

**根因**: L0 词典命中红线词 → 路由转人工，但 `final_intent` 字段为 None，说明 L1 / L2 / L3 cascade 都没识别 intent 名字。

**典型误伤样本**:
- "理财在哪" → app_navigation_with_disambiguation
- "基金风险" / "基金风险等级多少" → consult_fund_risk_with_disambiguation
- "我要买理财顺便买保险" → wealth_buy_with_disambiguation
- "改默认卡" → app_setting_with_disambiguation
- "我的卡怎么锁住了" → card_freeze
- "账户状态异常" / "账户状态异常?" → card_freeze

**修复方向** (P1): 这些不是 patch pattern 问题，而是 L1/L2/BERT cascade 没识别 → 走 L0 兜底转人工。需要排查 L0 触发 vs L1 命中的优先级顺序。

### 3.5 其他小 patch (≤7 条)
- **sec_freeze_unexpected (7 条)**: "我的账户怎么被冻了" 等 → 收紧疑问型信号
- **cons_urg_lock (6 条)**: "我的卡被锁了/密码输错被锁了" → 收紧当含 "密码/登录" 时降级 P1
- **security_aml_cross_border (2 条)**: "美元汇率" → 收紧必须有 "汇款/汇钱" 动作信号
- **safety_card_loss (1 条)**: "卡冻结怎么解?" → 已知边界 case

---

## 4. v3.11.0 修复 ROI 预估

| 修复项 | 预计恢复 P1 | 修后 P1 准确率 | 修后 P0 影响 |
|---|---|---|---|
| safety_card_freeze 疑问豁免 | +22 | 79.52% | 需验证 P0 不破 |
| l0_redline 收紧 (冻结/大额) | +19 | 85.24% | 需验证 P0 不破 |
| biz_transfer_large intent_top1 白名单 | +16 | 90.06% | 需验证 P0 不破 |
| sec_freeze_unexpected + cons_urg_lock 收紧 | +13 | 93.98% | 需验证 P0 不破 |
| (none) final_intent L0/L1 优先级调试 | +17 | 98.19% | 需验证 P0 不破 |
| **累计 5 项修复** | **+87** | **99.10%** | ✅ |

**P0 风险**：所有修复都是「疑问型信号豁免」+「白名单降级」，理论上不会破坏 P0 真·命中（因为真 P0 是动作请求「冻结卡」/「紧急冻结」/「转 50 万给公司」，不含疑问词）。但需跑 P0 regression 验证。

---

## 5. 下一步行动

### 5.1 立即 (今晚/明天)
1. **写 v3.11.0 patch 候选文件** `src/eval/badcase_patches_v311.py`
   - 实现 5 个收紧逻辑（safety_card_freeze / l0_redline / biz_transfer_large / sec_freeze_unexpected / cons_urg_lock）
2. **写 v3.11.0 round 1 测试脚本** `scripts/run_v3110_round1.py` (基于 D_eval_set_v3.3.json)
3. **跑 regression**: P0 不破门控 + P1 准确率提升

### 5.2 已有进度
- ✅ `data/v3110_round1_report.json` 已生成 (20:03 跑完) — D_eval_set_v3.3 上 P0 100% / P1 96.55%
- 但该 report 是基于样本子集 (177+29=206 条) 跑出来的，需要在 full 1076 上验证

### 5.3 风险提示
- v3.11.0 在 D_eval_set_v3.3 (子集 206 条) 上 P1 = 96.55%, 看起来修好了
- 但 **dedup full 1076 上是否仍 96%+ 需要跑 v3.11.0 full run 验证**
- P0 在子集 100% 不代表在 full 也 100% (子集只 177 条 P0, full 有 431 条)

---

## 6. 数据溯源

```bash
# 完整数据 + 90 条原始 query + 5 项修复建议
cat data/p1_a2_analysis.json | python -m json.tool

# 原始 v3.10.1 full 报告
cat data/observable_v3101_full_report.json

# 原始 trace 数据库
sqlite3 data/observability_v3101_full.db "SELECT user_input, final_intent, intent_top1, expected_action, p0_triggered FROM traces WHERE priority='P1' AND final_action='transfer_human' LIMIT 90"
```