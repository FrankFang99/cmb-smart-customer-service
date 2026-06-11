"""
v3.4.0 真 LLM 评测 — 600 样本端到端跑通
=========================================

对比 v3.2 mock 字符匹配:
- v3.2: 纯规则/字符, 不调 LLM, 52.5% 意图准确率 (mock 字符匹配)
- v3.4.0: 真 LLM 订阅 Key + api.minimaxi.com, 端到端 Pipeline

评估维度 (5 个, 对齐 v3.2):
1. intent_accuracy: 真实意图 vs 标注意图
2. p0_recall: P0 样本的 L0 触发率 (越权/反诈/AML)
3. l0_compliance: L0 触发后 AI 不答业务 (compliance)
4. rag_hit_rate: RAG 检索到相关知识
5. transfer_accuracy: 转人工准确率 (P0/越权 都应转)

输入: data/evaluation_dataset_v5.1.json (600 样本)
输出: data/eval_results_v340.json (详细结果 + 统计)

用法:
    py -3 scripts/eval_v340_real_llm.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Any


_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


from src.agent.e2e_pipeline import create_e2e_pipeline
from src.components.intent_recognizer import IntentRecognizer


# 评测集路径
DATASET_PATH = _ROOT / "data" / "evaluation_dataset_v5.1.json"
OUTPUT_PATH = _ROOT / "data" / "eval_results_v340.json"


# 评分逻辑
def evaluate_sample(pipeline, intent_recognizer, sample: Dict) -> Dict:
    """
    跑一个样本, 评估 5 维度
    """
    question = sample["question"]
    expected_intent = sample["intent"]
    is_p0_label = sample.get("is_p0", False)

    t0 = time.time()
    try:
        e2e = pipeline.handle(question, session_id=f"eval_{sample['id']}")
    except Exception as e:
        return {
            "sample_id": sample["id"],
            "question": question,
            "expected_intent": expected_intent,
            "is_p0_label": is_p0_label,
            "error": str(e),
            "intent_match": False,
            "p0_recall": False,
            "l0_compliance": False,
            "rag_hit": False,
            "transfer_correct": False,
            "elapsed_ms": 0,
        }

    t_total = (time.time() - t0) * 1000

    # 1. 意图准确率: e2e 识别的意图 vs 标注意图
    actual_intent = e2e.get("intent", "unknown")
    intent_match = actual_intent == expected_intent

    # 2. P0 Recall: P0 样本是否触发 L0 转人工
    p0_recall = e2e.get("l0_triggered", False) if is_p0_label else None

    # 3. L0 Compliance: L0 触发后 AI 没答业务 (回答应该是模板话术, 不是 LLM 答)
    if e2e.get("l0_triggered"):
        l0_compliance = e2e.get("action") == "transfer_human" and "llm_elapsed_ms" not in e2e
    else:
        l0_compliance = None  # 不适用

    # 4. RAG 命中: 业务类 (非 L0) 样本是否检索到 ≥1 条知识
    rag_hit = False
    if not e2e.get("l0_triggered"):
        rag_hit = len(e2e.get("sources", [])) > 0

    # 5. 转人工准确率: P0 样本应转人工, 非 P0 不应转
    if is_p0_label:
        transfer_correct = e2e.get("action") == "transfer_human"
    else:
        # 非 P0 样本, 期望 AI 答业务 (不转人工)
        transfer_correct = e2e.get("action") == "answer"

    return {
        "sample_id": sample["id"],
        "question": question,
        "expected_intent": expected_intent,
        "actual_intent": actual_intent,
        "is_p0_label": is_p0_label,
        "intent_match": intent_match,
        "p0_recall": p0_recall,
        "l0_compliance": l0_compliance,
        "rag_hit": rag_hit,
        "transfer_correct": transfer_correct,
        "action": e2e.get("action"),
        "l0_triggered": e2e.get("l0_triggered", False),
        "elapsed_ms": round(t_total, 1),
    }


def aggregate_results(results: List[Dict]) -> Dict:
    """
    汇总 5 维度指标
    """
    total = len(results)

    # 1. 意图准确率 (整体)
    intent_correct = sum(1 for r in results if r.get("intent_match"))
    intent_accuracy = intent_correct / total if total else 0

    # 2. P0 Recall (P0 样本中 L0 触发率)
    p0_samples = [r for r in results if r.get("is_p0_label")]
    p0_recall = (
        sum(1 for r in p0_samples if r.get("p0_recall")) / len(p0_samples)
        if p0_samples else 0
    )

    # 3. L0 Compliance (L0 触发后, AI 不答业务的合规率)
    l0_samples = [r for r in results if r.get("l0_triggered")]
    l0_compliance = (
        sum(1 for r in l0_samples if r.get("l0_compliance")) / len(l0_samples)
        if l0_samples else 0
    )

    # 4. RAG 命中率 (非 L0 样本)
    non_l0_samples = [r for r in results if not r.get("l0_triggered")]
    rag_hit = (
        sum(1 for r in non_l0_samples if r.get("rag_hit")) / len(non_l0_samples)
        if non_l0_samples else 0
    )

    # 5. 转人工准确率
    transfer_correct = sum(1 for r in results if r.get("transfer_correct"))
    transfer_accuracy = transfer_correct / total if total else 0

    # 业务大类分组 (按 intent 前缀)
    by_intent_group: Dict[str, Dict] = defaultdict(lambda: {"total": 0, "correct": 0})
    for r in results:
        group = r.get("expected_intent", "unknown").split("_")[0]
        by_intent_group[group]["total"] += 1
        if r.get("intent_match"):
            by_intent_group[group]["correct"] += 1
    for g in by_intent_group:
        if by_intent_group[g]["total"]:
            by_intent_group[g]["accuracy"] = round(
                by_intent_group[g]["correct"] / by_intent_group[g]["total"], 4
            )

    # 失败样本
    failures = [r for r in results if not r.get("intent_match")]

    # 耗时
    total_elapsed = sum(r.get("elapsed_ms", 0) for r in results)

    return {
        "total_samples": total,
        "intent_accuracy": round(intent_accuracy, 4),
        "p0_recall": round(p0_recall, 4),
        "l0_compliance": round(l0_compliance, 4),
        "rag_hit_rate": round(rag_hit, 4),
        "transfer_accuracy": round(transfer_accuracy, 4),
        "p0_samples": len(p0_samples),
        "l0_triggered_samples": len(l0_samples),
        "by_intent_group": dict(by_intent_group),
        "failures_count": len(failures),
        "total_elapsed_ms": round(total_elapsed, 1),
        "avg_elapsed_ms": round(total_elapsed / total, 1) if total else 0,
    }


def main():
    print("=" * 80)
    print("v3.4.0 真 LLM 评测 (Cascade 路由) — 600 样本")
    print("=" * 80)

    # 加载评测集
    with open(DATASET_PATH, encoding="utf-8") as f:
        dataset = json.load(f)
    samples = dataset["samples"]
    print(f"评测集版本: {dataset['dataset_version']}, 总样本: {len(samples)}")
    print()

    # 初始化 e2e pipeline (内置 cascade 路由)
    pipeline = create_e2e_pipeline(k=3)
    intent_recognizer = IntentRecognizer()  # 给 e2e 内部用

    # 跑评测
    results = []
    cascade_counter = Counter()
    llm_called_count = 0
    t0 = time.time()
    for i, sample in enumerate(samples, 1):
        if i % 50 == 0 or i == 1:
            elapsed = time.time() - t0
            eta = (elapsed / i) * (len(samples) - i) if i > 0 else 0
            print(f"  进度 {i}/{len(samples)} ({i/len(samples)*100:.0f}%)  "
                  f"已用 {elapsed:.0f}s, 预计剩余 {eta:.0f}s")

        result = evaluate_sample(pipeline, intent_recognizer, sample)
        # 跑一次 e2e 来收集 cascade 信息 (重复跑, 浪费但简单)
        try:
            e2e_res = pipeline.handle(sample["question"], session_id=f"eval_c_{sample['id']}")
            result["cascade"] = e2e_res.get("cascade", "?")
            result["llm_called"] = e2e_res.get("llm_called", False)
            result["llm_elapsed_ms"] = e2e_res.get("llm_elapsed_ms", 0)
            cascade_counter[result["cascade"]] += 1
            if result["llm_called"]:
                llm_called_count += 1
        except Exception:
            pass

        results.append(result)

    total_elapsed = time.time() - t0
    print(f"\n  跑完 600 样本, 总耗时 {total_elapsed:.1f}s ({total_elapsed/60:.1f} 分钟)")

    # Cascade 统计
    print(f"\n  Cascade 路由分布:")
    for level, count in cascade_counter.most_common():
        print(f"    {level}: {count} ({count/len(samples)*100:.1f}%)")
    print(f"  LLM 调用率: {llm_called_count}/{len(samples)} = {llm_called_count/len(samples)*100:.1f}%")
    print(f"  LLM 调用节省: {len(samples) - llm_called_count}/{len(samples)} = {(len(samples) - llm_called_count)/len(samples)*100:.1f}%")

    # 汇总
    print("\n  汇总统计...")
    summary = aggregate_results(results)

    # 输出
    output = {
        "eval_version": "v3.4.0",
        "eval_date": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "llm": "MiniMax-M2.7 via api.minimaxi.com/v1 (订阅 Key)",
        "dataset_version": dataset["dataset_version"],
        "summary": summary,
        "cascade_distribution": dict(cascade_counter),
        "llm_call_rate": round(llm_called_count / len(samples), 4),
        "sample_results": results[:50],  # 只存前 50 详细 (避免文件过大)
        "failures_first_50": [r for r in results if not r.get("intent_match")][:50],
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2, default=str)
    print(f"  结果保存: {OUTPUT_PATH}")

    # 打印
    print("\n" + "=" * 80)
    print("v3.4.0 真 LLM 评测结果")
    print("=" * 80)
    print(f"总样本: {summary['total_samples']}")
    print(f"意图准确率: {summary['intent_accuracy']*100:.2f}%")
    print(f"P0 Recall: {summary['p0_recall']*100:.2f}% ({summary['p0_samples']} 样本)")
    print(f"L0 Compliance: {summary['l0_compliance']*100:.2f}% ({summary['l0_triggered_samples']} 触发)")
    print(f"RAG 命中率: {summary['rag_hit_rate']*100:.2f}%")
    print(f"转人工准确率: {summary['transfer_accuracy']*100:.2f}%")
    print(f"\n按大类分组:")
    for group, stat in sorted(summary["by_intent_group"].items(), key=lambda x: -x[1]["total"]):
        acc = stat.get("accuracy", 0) * 100
        print(f"  {group:15s} {stat['correct']:3d}/{stat['total']:3d} = {acc:.1f}%")
    print(f"\n失败样本: {summary['failures_count']}/{summary['total_samples']}")
    print(f"总耗时: {summary['total_elapsed_ms']/1000:.1f}s, 平均 {summary['avg_elapsed_ms']:.0f}ms/样本")


if __name__ == "__main__":
    main()
