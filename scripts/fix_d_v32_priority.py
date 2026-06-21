"""
fix_d_v32_priority.py - v3.6.2 PM 决策: 重新审视 P0 红线清单
====================================================================

背景:
  v3.6.1 评测发现 D_eval_set_v3.2.json 的 P0 召回率卡在 66.75%,
  而 21 个 P0 intent 中有 11 类本质是"业务敏感但非监管红线",
  PM 视角看这些 intent 标 P0 不合理 (查余额/尾号/开户行用短信验证即可,
  周三5折/M+福利/房贷利率是公开咨询/营销活动)。

决策 (方逸之, 2026-06-21):
  1. 保留 P0: 11 类 - 真正触发强转人工 / 反洗钱 / 反诈 / 适当性 / 投诉
     - safety_card_loss, sys_service_route_human, sys_service_complaint
     - security_fraud_recognize, security_fraud_report
     - security_aml_large_transfer, security_aml_cross_border
     - security_suitability_unrated, security_suitability_mismatch
     - security_promise_yield
     - biz_optout_outbound (金融营销外呼强监管)
     - biz_transfer_large (大额转账触发反洗钱审核)

  2. P0 -> P1: biz_password_reset, biz_statement_print
     (业务敏感, 需身份核验, 但非强转人工)

  3. P0 -> P2: info_account_balance, info_account_card_no,
                info_account_open_bank, consult_loan_mortgage
     (模板直出, 无强转人工要求)

  4. P0 -> P3: mkt_food_5off, mkt_member_monthly, mkt_member_upgrade
     (营销活动, 公开规则)

效果:
  - P0 总数: 21 -> 12 (实际数据从 827 -> ~420)
  - 银行红线条数不再被业务子类稀释, 真正反映"必须人工介入"
  - 业务子类的"高优先级"用 P1 表达, 与原 v3.1 设计一致

执行:
  python scripts/fix_d_v32_priority.py

作者: 方逸之
日期: 2026-06-21
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
IN_PATH = _ROOT / "data" / "D_eval_set_v3.2.json"
OUT_PATH = IN_PATH  # 原地更新

# 11 类 PM 调整后的优先级映射
PRIORITY_REMAP = {
    # P0 -> P1 (业务敏感但非红线, 保留较高优先级但不触发强转人工)
    "biz_password_reset": "P1",
    "biz_statement_print": "P1",
    # P0 -> P2 (模板直出/公开咨询)
    "info_account_balance": "P2",
    "info_account_card_no": "P2",
    "info_account_open_bank": "P2",
    "consult_loan_mortgage": "P2",
    # P0 -> P3 (营销活动, 公开规则)
    "mkt_food_5off": "P3",
    "mkt_member_monthly": "P3",
    "mkt_member_upgrade": "P3",
}

# 保持 P0 的 12 类 (新增 biz_transfer_large 显式列出)
KEEP_P0 = {
    # SAFETY
    "safety_card_loss",
    # SECURITY (7)
    "security_fraud_recognize", "security_fraud_report",
    "security_aml_large_transfer", "security_aml_cross_border",
    "security_suitability_unrated", "security_suitability_mismatch",
    "security_promise_yield",
    # SYSTEM
    "sys_service_route_human", "sys_service_complaint",
    # BIZ (真正红线)
    "biz_optout_outbound", "biz_transfer_large",
}


def main():
    print(f"读取 {IN_PATH}")
    data = json.loads(IN_PATH.read_text(encoding="utf-8"))
    samples = data["samples"]

    # 1. 重打 priority
    changed = Counter()
    old_p0_count = sum(1 for s in samples if s.get("priority") == "P0")

    for s in samples:
        intent = s["intent_top1"]
        old = s.get("priority")
        if intent in PRIORITY_REMAP:
            new = PRIORITY_REMAP[intent]
            if old != new:
                s["priority"] = new
                s["annotation_by"] = "pm_review_v362"
                s["annotation_date"] = "2026-06-21"
                s["review_status"] = "pm_reviewed"
                changed[(intent, old, new)] += 1

    # 2. 统计新的分布
    new_p0_count = sum(1 for s in samples if s.get("priority") == "P0")
    new_p1_count = sum(1 for s in samples if s.get("priority") == "P1")
    new_p2_count = sum(1 for s in samples if s.get("priority") == "P2")
    new_p3_count = sum(1 for s in samples if s.get("priority") == "P3")

    p0_by_intent = Counter()
    for s in samples:
        if s.get("priority") == "P0":
            p0_by_intent[s["intent_top1"]] += 1

    # 3. 校验: KEEP_P0 必须全部命中
    missing = KEEP_P0 - set(p0_by_intent.keys())
    extra = set(p0_by_intent.keys()) - KEEP_P0
    if missing or extra:
        raise AssertionError(
            f"P0 intent 校验失败!\n"
            f"  缺失 (应保留为 P0 但未命中): {missing}\n"
            f"  多出 (不应是 P0): {extra}\n"
            f"  当前 P0 intent: {sorted(p0_by_intent.keys())}"
        )

    # 4. 更新元数据
    data["p0_count"] = new_p0_count
    data["p1_count"] = new_p1_count
    data["p2_count"] = new_p2_count
    data["p3_count"] = new_p3_count
    data["intent_coverage"]["p0_total"] = len(KEEP_P0)
    data["intent_coverage"]["p0_covered"] = len(p0_by_intent)
    data["annotation_team"] = [
        *data.get("annotation_team", []),
        "pm_review_v362 (方逸之, 2026-06-21, 重审 11 类非红线 P0)",
    ]
    data["description"] = (
        "v3.2 黄金评测集 (1500 条): 复用 v8.0 (800) + P0 变体 (350) + 多意图 (200) + 边缘 (100) + 改写 (50). "
        "v3.6.2 PM 重审: 21 P0 -> 12 P0, 11 类业务子类 (INFO/BIZ/CONSULT/MARKETING) 降级为 P1/P2/P3. "
        "P0 仅保留 SAFETY/SECURITY/强转人工/投诉/营销外呼/大额转账共 12 类真正监管红线."
    )

    # 5. 写回
    OUT_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # 6. 报告
    print()
    print("=" * 60)
    print("v3.6.2 PM Priority 重审报告")
    print("=" * 60)
    print(f"\n样本总数: {len(samples)}")
    print(f"\n优先级分布变化:")
    print(f"  P0: {old_p0_count} -> {new_p0_count} (-{old_p0_count - new_p0_count})")
    print(f"  P1: {data['p1_count']}")
    print(f"  P2: {data['p2_count']}")
    print(f"  P3: {data['p3_count']}")
    print(f"\nP0 红线 intent (新, 12 类):")
    for intent, cnt in sorted(p0_by_intent.items(), key=lambda x: -x[1]):
        marker = " [保持 P0]" if intent in KEEP_P0 else " ⚠️ 应非 P0"
        print(f"  {cnt:4d}  {intent}{marker}")
    print(f"\n重打样本数 (按 intent 变化):")
    for (intent, old, new), cnt in sorted(changed.items()):
        print(f"  {intent}: {old} -> {new}, {cnt} 条")
    print(f"\n写入 {OUT_PATH}")
    print(f"\n✅ 校验通过: P0 intent 数 = {len(p0_by_intent)}, 与目标 12 一致")


if __name__ == "__main__":
    main()