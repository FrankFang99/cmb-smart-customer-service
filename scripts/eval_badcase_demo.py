"""
v3.4.0 Badcase 演示标注
=======================

演示 PM 标注流程: 3 条 badcase 标注 + 修复
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.eval.badcase_pool import BadcasePool


def main():
    pool = BadcasePool()
    print(f"Records: {len(pool.records)}")

    # 1. SMART_00407 "申请信用卡" - cons vs sales 混淆
    # 修复: 让 "申请" 也能匹配 cons_prod_credit
    ok = pool.label_badcase(
        sample_id="SMART_00407",
        root_cause="intent_mismatch",
        fix_action="add_intent_pattern",
        p_level="P1",
        fix_note="在意图识别规则中, 让 '申请信用卡' / '我想办信用卡' 同时匹配 cons_prod_credit (咨询) 和 sales_credit_prod (营销). 当前规则偏向 sales, 但客户问的多是产品咨询.",
    )
    print(f"SMART_00407 labeled: {ok}")

    # 2. SMART_00680 "被诈骗了" - 应强转人工, 补 L0 触发
    ok = pool.label_badcase(
        sample_id="SMART_00680",
        root_cause="l0_miss_trigger",
        fix_action="add_faq",
        p_level="P0",
        fix_note="'被诈骗了' 应触发 L0 反诈骗红线 + 100% 转人工 + 提示 '请立即挂失 + 报警 110'. 实际走了 sec_fraud_report 模板, 未强转人工, 不符合银行业 P0 红线.",
    )
    print(f"SMART_00680 labeled: {ok}")
    # 一键入 KB
    new_answer = (
        "非常理解您的心情! 请您立即采取以下措施:\n"
        "1. 第一时间挂失: 拨打 95555 转人工挂失所有招行卡片\n"
        "2. 立即报警: 拨打 110 报警, 保留报警回执\n"
        "3. 保留证据: 诈骗电话/短信/转账截图\n"
        "4. 招行反诈中心: 7×24 热线 95555 转 9\n"
        "我行不会通过电话/短信索要您的密码/验证码, 请提高警惕."
    )
    kb_ok = pool.add_faq_to_kb(
        sample_id="SMART_00680",
        new_answer=new_answer,
        domain="service",
    )
    print(f"SMART_00680 -> KB: {kb_ok}")

    # 3. SMART_00315 "转人工" - cons_urg_human 应强转人工
    ok = pool.label_badcase(
        sample_id="SMART_00315",
        root_cause="cascade_routing_err",
        fix_action="adjust_threshold",
        p_level="P0",
        fix_note="'转人工' 应 100% 转人工 (cascade L0), 不该走 L2 RAG 模板. 在 cascade 路由中, cons_urg_human 强制 L0 转人工, 不论 intent_conf.",
    )
    print(f"SMART_00315 labeled: {ok}")

    # 4. SMART_00264 "转账到别的银行" - 应是 biz_tran_external 走了 info_prog_transfer
    ok = pool.label_badcase(
        sample_id="SMART_00264",
        root_cause="intent_mismatch",
        fix_action="add_intent_pattern",
        p_level="P1",
        fix_note="'转账到别的银行' 包含 '转账' + '别的银行' 应匹配 biz_tran_external. 当前规则把 '别的银行' 当查询走了 info_prog_transfer. 加规则: '别的银行'/'跨行'/'他行' 强匹配 biz_tran_external.",
    )
    print(f"SMART_00264 labeled: {ok}")

    print("\n=== After labeling ===")
    summary = pool.weekly_summary()
    for k, v in summary.items():
        if k in ("p0_open_samples", "p1_open_samples"):
            print(f"  {k}: {len(v)} items")
        else:
            print(f"  {k}: {v}")

    # 重导周报
    out = PROJECT_ROOT / "data" / "badcase" / "weekly_report.md"
    pool.export_markdown(str(out))
    print(f"\nExported weekly report: {out}")


if __name__ == "__main__":
    main()
