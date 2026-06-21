"""
v3.7.0 E2E Pipeline 真实 case demo
===================================

定位: 面试展示用 10 个典型 case, 覆盖 5 路径 + 多轮澄清 + L0 红线
每个 case 展示完整链路 (意图识别 / 5 路径 / cascade / 幻觉检测 / 多轮)

输出:
- data/e2e_demo_v37.json  (结构化, 给面试官)
- data/e2e_demo_v37.md    (Markdown, 贴 GitHub)
- data/e2e_demo_v37.txt   (纯文本, 控制台展示)
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


from src.agent.e2e_pipeline_v37 import E2EPipelineV37, create_e2e_pipeline_v37


# ============================================================
# 10 个真实 case, 覆盖 5 路径 + 多轮澄清 + L0 红线
# ============================================================
DEMO_CASES = [
    # ============== 1. L0_HUMAN: 反诈红线 ==============
    {
        "category": "L0_HUMAN (银行业 P0 红线)",
        "scenario": "用户遭遇冒充公检法诈骗, 已转账",
        "user_input": "我刚给一个自称是公安的人转了 5 万块, 他说我不转就冻结我账户, 现在我慌了",
        "expected_industry_action": "立即转人工, 上报反诈中心",
    },
    # ============== 2. L0_HUMAN: 卡片挂失 ==============
    {
        "category": "L0_HUMAN (银行业 P0 红线)",
        "scenario": "用户信用卡丢失",
        "user_input": "我的信用卡刚才在商场丢了, 我担心被人盗刷",
        "expected_industry_action": "立即挂失 + 转人工核实身份",
    },
    # ============== 3. BIZ_DB: 业务数据库查询 ==============
    {
        "category": "BIZ_DB (业务数据库查询)",
        "scenario": "用户查询本月账单",
        "user_input": "我这个月信用卡账单多少钱?",
        "expected_industry_action": "调用账单系统, 返回金额 + 还款日",
    },
    # ============== 4. BIZ_DB: 物流查询 ==============
    {
        "category": "BIZ_DB (业务数据库查询)",
        "scenario": "用户查询新卡邮寄状态",
        "user_input": "我新办的信用卡寄到哪了?",
        "expected_industry_action": "调用物流系统, 返回快递单号 + 状态",
    },
    # ============== 5. AGENT: 工具意图 ==============
    {
        "category": "AGENT_TOOL (工具意图, 跳转 App)",
        "scenario": "用户要激活新卡",
        "user_input": "我刚收到新卡, 怎么激活?",
        "expected_industry_action": "给 App 跳转链接 + 操作步骤",
    },
    # ============== 6. CASCADE_L1: 业务办理 L1 模板 ==============
    {
        "category": "CASCADE L1 (业务办理, 模板直接答)",
        "scenario": "用户查询转账限额",
        "user_input": "我手机银行一天能转多少钱?",
        "expected_industry_action": "模板直接答: 单笔 5 万 / 单日 20 万",
    },
    # ============== 7. CASCADE_L2: RAG 检索 ==============
    {
        "category": "CASCADE L2 (中等置信, RAG 命中)",
        "scenario": "用户咨询理财产品",
        "user_input": "稳健一点的理财产品有哪些? 收益大概多少?",
        "expected_industry_action": "RAG 检索知识库 + 风险提示",
    },
    # ============== 8. RAG: 信息咨询 ==============
    {
        "category": "RAG_KB (信息咨询)",
        "scenario": "用户查询招行客服电话",
        "user_input": "招行信用卡客服电话多少?",
        "expected_industry_action": "知识库检索: 400-880-5535",
    },
    # ============== 9. 多轮澄清: 槽位缺失 ==============
    {
        "category": "CASCADE 多轮澄清 (槽位缺失)",
        "scenario": "用户要转账但没说金额/收款人",
        "user_input": "我要转一笔钱",
        "expected_industry_action": "追问: 转给谁? 多少金额? 哪个银行?",
    },
    # ============== 10. 投诉 ==============
    {
        "category": "L0_HUMAN (银行业 P0 红线 - 投诉)",
        "scenario": "用户强烈不满, 投诉客服态度",
        "user_input": "你们这个 AI 客服太差了, 完全答非所问! 我要投诉!",
        "expected_industry_action": "升级到 95555 客服专员, 24h 回访",
    },
]


def run_demo(pipeline: E2EPipelineV37) -> List[Dict[str, Any]]:
    """跑所有 demo case"""
    results = []
    for i, case in enumerate(DEMO_CASES, 1):
        print(f"\n--- Case {i:02d}: {case['category']} ---")
        print(f"场景: {case['scenario']}")
        print(f"用户: {case['user_input']}")
        print(f"期望: {case['expected_industry_action']}")
        print(f"---")
        print(f"链路执行:")

        # 跑 E2E
        t0 = time.time()
        result = pipeline.handle(
            case["user_input"],
            session_id=f"demo_case_{i}",
        )
        elapsed_ms = (time.time() - t0) * 1000

        d = result.to_dict()

        # 打印链路
        print(f"  [1] 意图识别: {d['intent']} (置信 {d['intent_confidence']:.2f})")
        if d['l0_triggered']:
            print(f"  [2] L0 红线触发: {len(d['l0_categories'])} 个类别")
            for cat in d['l0_categories'][:2]:
                print(f"      - {cat.get('category', '?')}: {cat.get('sub_category', '?')}")
        print(f"  [3] 5 路径路由: {d['path']}")
        print(f"      理由: {d['extra'].get('route_reason', 'N/A')[:80]}")
        if d['cascade_level']:
            print(f"  [4] Cascade 层: {d['cascade_level']} ({d['action']})")
        else:
            print(f"  [4] 最终动作: {d['action']}")
        if d['sources']:
            print(f"  [5] 引用来源: {d['sources'][:3]}")
        if d['hallucination_check']:
            hc = d['hallucination_check']
            print(f"  [6] 幻觉检测: score={hc['score']:.2f} action={hc['action']}")
        if d['needs_clarification']:
            print(f"  [7] 多轮澄清: 缺失槽位 {d['missing_slots']}")
        print(f"  [答] {d['answer'][:200]}{'...' if len(d['answer']) > 200 else ''}")
        print(f"  [耗时] {d['elapsed_ms']}ms (含 1+2+3+4+5+6 完整链路)")

        results.append({
            "case_id": i,
            "category": case["category"],
            "scenario": case["scenario"],
            "user_input": case["user_input"],
            "expected_industry_action": case["expected_industry_action"],
            "result": d,
            "elapsed_ms": elapsed_ms,
        })

    return results


def generate_markdown(results: List[Dict]) -> str:
    """生成 .md 报告"""
    lines = []
    lines.append("# v3.7.0 E2E Pipeline 真实 case 演示 (面试用)")
    lines.append("")
    lines.append("> 展示完整 6 阶段端到端链路: **意图识别 → L0 红线 → 5 路径路由 → Cascade → 幻觉检测 → 多轮澄清**")
    lines.append("")
    lines.append("---")
    lines.append("")
    for r in results:
        lines.append(f"## Case {r['case_id']:02d}: {r['category']}")
        lines.append("")
        lines.append(f"**场景**: {r['scenario']}")
        lines.append("")
        lines.append(f"**用户输入**: `{r['user_input']}`")
        lines.append("")
        lines.append(f"**业界期望动作**: {r['expected_industry_action']}")
        lines.append("")
        d = r["result"]
        lines.append("**v3.7.0 E2E Pipeline 完整链路**:")
        lines.append("")
        lines.append(f"1. **意图识别**: `{d['intent']}` (置信度 {d['intent_confidence']:.2f})")
        if d['l0_triggered']:
            lines.append(f"2. **L0 红线触发**: {len(d['l0_categories'])} 个类别")
            for cat in d['l0_categories'][:3]:
                lines.append(f"   - `{cat.get('category', '?')}`: {cat.get('sub_category', '?')}")
        else:
            lines.append("2. **L0 红线**: 未触发")
        lines.append(f"3. **5 路径路由**: `{d['path']}`")
        lines.append(f"   - 路由理由: {d['extra'].get('route_reason', 'N/A')[:120]}")
        if d['cascade_level']:
            lines.append(f"4. **Cascade 层**: `{d['cascade_level']}` (动作: `{d['action']}`)")
        else:
            lines.append(f"4. **最终动作**: `{d['action']}`")
        if d['sources']:
            lines.append(f"5. **引用来源**: {', '.join(d['sources'][:3])}")
        if d['hallucination_check']:
            hc = d['hallucination_check']
            lines.append(f"6. **幻觉检测**: score={hc['score']:.2f}, action={hc['action']}")
        if d['needs_clarification']:
            lines.append(f"7. **多轮澄清**: 缺失槽位 {d['missing_slots']}")
        lines.append("")
        lines.append(f"**答案**:")
        lines.append("")
        lines.append(f"> {d['answer']}")
        lines.append("")
        lines.append(f"_耗时: {d['elapsed_ms']}ms / 实际耗时(含评测开销): {r['elapsed_ms']:.1f}ms_")
        lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines)


def generate_text(results: List[Dict]) -> str:
    """生成 .txt 报告 (控制台友好)"""
    lines = []
    lines.append("=" * 80)
    lines.append("v3.7.0 E2E Pipeline 真实 case 演示")
    lines.append("=" * 80)
    for r in results:
        lines.append("")
        lines.append(f"### Case {r['case_id']:02d}: {r['category']}")
        lines.append(f"场景: {r['scenario']}")
        lines.append(f"用户: {r['user_input']}")
        lines.append(f"业界期望: {r['expected_industry_action']}")
        d = r["result"]
        lines.append(f"")
        lines.append(f"v3.7.0 E2E Pipeline 链路:")
        lines.append(f"  1. 意图识别: {d['intent']} (置信 {d['intent_confidence']:.2f})")
        if d['l0_triggered']:
            lines.append(f"  2. L0 红线: 触发 {len(d['l0_categories'])} 类")
        else:
            lines.append(f"  2. L0 红线: 未触发")
        lines.append(f"  3. 5 路径: {d['path']}")
        if d['cascade_level']:
            lines.append(f"  4. Cascade: {d['cascade_level']} -> {d['action']}")
        else:
            lines.append(f"  4. 动作: {d['action']}")
        if d['sources']:
            lines.append(f"  5. 引用: {d['sources'][:3]}")
        if d['hallucination_check']:
            lines.append(f"  6. 幻觉: score={d['hallucination_check']['score']:.2f}")
        if d['needs_clarification']:
            lines.append(f"  7. 追问: {d['missing_slots']}")
        lines.append(f"")
        lines.append(f"答案: {d['answer'][:300]}")
        lines.append(f"耗时: {d['elapsed_ms']}ms")
        lines.append("-" * 80)
    return "\n".join(lines)


def main():
    print("初始化 v3.7.0 E2E Pipeline (enable_llm=False, 离线安全)...")
    pipeline = create_e2e_pipeline_v37(enable_llm=False, customer_id="C001")
    print(f"Pipeline 初始化完成")
    print()
    print("=" * 80)
    print("v3.7.0 E2E Pipeline 真实 case demo (10 个 case 覆盖 5 路径 + 多轮澄清 + L0)")
    print("=" * 80)

    results = run_demo(pipeline)

    # 输出报告
    md_path = _ROOT / "data" / "e2e_demo_v37.md"
    txt_path = _ROOT / "data" / "e2e_demo_v37.txt"
    json_path = _ROOT / "data" / "e2e_demo_v37.json"

    md_path.write_text(generate_markdown(results), encoding="utf-8")
    txt_path.write_text(generate_text(results), encoding="utf-8")
    json_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print()
    print("=" * 80)
    print(f"[OK] Markdown 报告: {md_path}")
    print(f"[OK] TXT 报告: {txt_path}")
    print(f"[OK] JSON 详情: {json_path}")


if __name__ == "__main__":
    main()
