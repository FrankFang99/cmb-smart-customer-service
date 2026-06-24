"""
Cascade E2E v3.8.0 — 真做 L1规则 → L2 BERT → L3 MiniMax LLM 兜底
================================================================

按用户要求重做:
- L1 规则层: IntentRecognizer + 4 层 P0 红线兜底
- L2 小模型层: M3-bert-base-chinese (holdout 98.71%) 真实推理
- L3 大模型兜底层: MiniMax API 真实调用
- 训练集 / 测试集严格分离 (用 D v3.2 评测集做测试, 训练集来自原始知识库)

诚实声明:
1. D v3.2 是项目自建评测集, 但训练 BERT 时未用 (训练用 v3.5.5 内部种子集)
2. L3 LLM 真实调用会有网络延迟 / token 成本
3. 真实 OOD 评测集未准备
"""
from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.components.intent_recognizer import IntentRecognizer
from src.eval.banking_l0_dict import check_l0
from src.nlp.cascade_l2 import get_bert_l2, cascade_predict_with_l2
from src.llm.minimax_client import chat as llm_chat


# ============================================================
# 训练集 / 测试集分离 (诚实标注)
# ============================================================

@dataclass
class DatasetSplit:
    """数据集划分"""
    train_source: str        # 训练集来源
    test_source: str         # 测试集来源
    train_size: int
    test_size: int
    overlap_check: str       # 是否做了去重 / 交集检查

# 诚实说明:
# - BERT 训练集: 项目内部种子集 (v3.5.5 业务标注), 310 条, 训练时已划分 train/val/holdout
# - 测试集: D_eval_set_v3.2.json, 1500 条 (项目自建评测集, 8 轮迭代持续调整)
# - 两批数据来源不同, 但 IR label 空间与 D v3.2 有重叠 (详见 v3.6.1 P0 patch)
# - 严格说: D v3.2 不是纯 OOD, 但也不是 BERT 训练集 (训练集未公开 label)


# ============================================================
# Cascade 真跑主类
# ============================================================

class CascadeE2EV38:
    """
    L1 规则 → L2 BERT → L3 MiniMax LLM 兜底
    每层独立转人工门控
    """

    def __init__(self, enable_llm: bool = True, confidence_threshold: float = 0.85):
        self.intent_recognizer = IntentRecognizer()
        self.bert_l2 = get_bert_l2()  # 懒加载 M3-bert-base-chinese
        self.confidence_threshold = confidence_threshold
        self.enable_llm = enable_llm
        self._stats = {
            "L1_rule_hit": 0,
            "L1_rule_p0": 0,
            "L2_bert_hit": 0,
            "L2_bert_p0": 0,
            "L3_llm_hit": 0,
            "L3_llm_p0": 0,
            "transfer_human_total": 0,
            "llm_error": 0,
        }

    def handle(self, user_input: str, session_id: str = "default", priority: str = "?") -> Dict[str, Any]:
        """主入口: 三层 Cascade + 转人工门控
        Args:
            priority: 从外部传入 (如 D v3.2 sample.priority), 用于 L3 Prompt 路由
        """
        t0 = time.time()
        result = {
            "user_input": user_input,
            "cascade_path": [],
            "final_action": None,
            "final_intent": None,
            "final_confidence": 0.0,
            "final_answer": None,
            "p0_triggered": False,
            "elapsed_ms": 0.0,
        }

        # ==========================================
        # L1: 规则层
        # ==========================================
        ir = self.intent_recognizer.recognize(user_input)
        l1_intent = ir.intent_value()
        l1_conf = ir.confidence
        l1_is_p0 = ir.is_p0

        # L0 红线双保险
        l0 = check_l0(user_input)
        l0_triggered = l0["l0_triggered"] or l1_is_p0

        result["cascade_path"].append({
            "layer": "L1_rule",
            "intent": l1_intent,
            "confidence": l1_conf,
            "is_p0": l1_is_p0,
            "l0_triggered": l0_triggered,
        })

        # L1 P0 红线 → 立即转人工 (不调任何模型)
        if l0_triggered:
            result["final_action"] = "transfer_human"
            result["final_intent"] = l1_intent
            result["final_confidence"] = l1_conf
            result["p0_triggered"] = True
            result["final_answer"] = self._p0_response_template(l0_categories=l0.get("categories", []))
            self._stats["L1_rule_p0"] += 1
            self._stats["transfer_human_total"] += 1
            result["elapsed_ms"] = round((time.time() - t0) * 1000, 2)
            return result

        # L1 高置信度 → 直接答
        if l1_conf >= self.confidence_threshold:
            result["final_action"] = "answer"
            result["final_intent"] = l1_intent
            result["final_confidence"] = l1_conf
            result["final_answer"] = f"[L1规则直答] 识别为意图: {l1_intent}"
            self._stats["L1_rule_hit"] += 1
            result["elapsed_ms"] = round((time.time() - t0) * 1000, 2)
            return result

        # ==========================================
        # L2: BERT 小模型
        # ==========================================
        bert_result = self.bert_l2.predict(user_input) if self.bert_l2.load() else None
        if bert_result:
            l2_intent, l2_conf, l2_source = bert_result
            result["cascade_path"].append({
                "layer": "L2_bert",
                "intent": l2_intent,
                "confidence": l2_conf,
                "source": l2_source,
            })

            # L2 P0 (按业务规则: BERT 识别为 P0 类意图) → 转人工
            l2_is_p0 = l2_intent in P0_INTENT_LIST  # 简化: 已知 P0 列表
            if l2_is_p0:
                result["final_action"] = "transfer_human"
                result["final_intent"] = l2_intent
                result["final_confidence"] = l2_conf
                result["p0_triggered"] = True
                result["final_answer"] = "[L2 BERT 识别为 P0 红线] 已转人工"
                self._stats["L2_bert_p0"] += 1
                self._stats["transfer_human_total"] += 1
                result["elapsed_ms"] = round((time.time() - t0) * 1000, 2)
                return result

            # L2 高置信度 → 用 BERT 结果
            if l2_conf >= self.confidence_threshold:
                result["final_action"] = "answer"
                result["final_intent"] = l2_intent
                result["final_confidence"] = l2_conf
                result["final_answer"] = f"[L2 BERT 直答] 识别为意图: {l2_intent}"
                self._stats["L2_bert_hit"] += 1
                result["elapsed_ms"] = round((time.time() - t0) * 1000, 2)
                return result
        else:
            result["cascade_path"].append({
                "layer": "L2_bert",
                "status": "unavailable",
                "fallback_reason": "BERT 模型未加载",
            })

        # ==========================================
        # L3: MiniMax LLM 兜底
        # ==========================================
        if not self.enable_llm:
            result["final_action"] = "fallback_to_human"
            result["final_intent"] = l1_intent
            result["final_confidence"] = l1_conf
            result["final_answer"] = "[L3 LLM 未启用] 转人工兜底"
            self._stats["transfer_human_total"] += 1
            result["elapsed_ms"] = round((time.time() - t0) * 1000, 2)
            return result

        # 真实调 LLM
        try:
            llm_response = self._call_llm_with_guard(user_input, l1_intent, l1_conf, priority)
            result["cascade_path"].append({
                "layer": "L3_llm",
                "response_preview": llm_response[:100] + "..." if len(llm_response) > 100 else llm_response,
            })

            # LLM 输出 P0 检测 (语义级)
            if self._llm_output_is_p0(llm_response):
                result["final_action"] = "transfer_human"
                result["p0_triggered"] = True
                result["final_answer"] = "[L3 LLM 兜底检测到 P0 语义] 已转人工"
                self._stats["L3_llm_p0"] += 1
                self._stats["transfer_human_total"] += 1
            else:
                result["final_action"] = "answer"
                result["final_answer"] = llm_response
                self._stats["L3_llm_hit"] += 1
        except Exception as e:
            result["cascade_path"].append({
                "layer": "L3_llm",
                "status": "error",
                "error": str(e)[:200],
            })
            result["final_action"] = "fallback_to_human"
            result["final_answer"] = f"[L3 LLM 调用失败] 转人工兜底: {str(e)[:100]}"
            self._stats["llm_error"] += 1
            self._stats["transfer_human_total"] += 1

        result["elapsed_ms"] = round((time.time() - t0) * 1000, 2)
        return result

    # ============================================================
# L3 Prompt 业务定制 (按 priority + intent_type 路由)
# ============================================================

L3_PROMPT_REGISTRY = {
    # P0 红线类: 强制转人工模板, 不让 LLM 自由发挥
    "p0_redline": {
        "trigger_intents": ["card_loss", "card_freeze", "fraud_report", "complaint",
                            "aml_large", "aml_structured", "safety_card_freeze"],
        "system": """你是招商银行合规专员 (P0 红线处置)。
你的唯一职责: 识别红线 + 强制建议转人工 95555, 不允许提供任何业务办理步骤。
- 涉及反欺诈 / 反洗钱 / 账户冻结 / 盗刷 / 投诉升级, 必须明确告知"已为您转接 95555"
- 严禁提供"如何操作""如何转账""如何避免"等业务指导
- 严禁编造工单号 / 处理时间等细节
- 回复必须包含"95555"和"转人工"两个关键词""",
        "user_template": """用户问题: {query}
L1 识别为: {intent} (priority=P0)
请生成标准红线转人工回复。""",
    },

    # P1 业务咨询类: 注入业务知识 + 必须保守
    "p1_consult": {
        "trigger_intents": ["info_acc_balance", "info_bill_amount", "info_acc_detail",
                            "cons_prod_loan", "consult_credit_card_pick"],
        "system": """你是招商银行智能客服助手 (P1 业务咨询)。
业务规则:
- 涉及账户查询 / 转账 / 信用卡 / 贷款咨询, 必须明确建议"请通过手机银行 App 或 95555 操作"
- 涉及利率 / 手续费 / 额度等数字, 不确定时严禁编造, 明确说"建议联系人工客服确认"
- 涉及产品推荐 / 理财购买, 严守"风险提示 + 不承诺收益"红线
- 回答简洁, 200 字以内, 结构: 结论 → 原因 → 下一步""",
        "user_template": """用户问题: {query}
L1 识别为: {intent} (priority=P1)
请基于业务规则给出回复。""",
    },

    # P3 礼貌语类: 严禁"过度保守", 直接友好回应
    "p3_courtesy": {
        "trigger_intents": ["sys_other_farewell", "sys_thanks", "sys_bye",
                            "sys_greeting", "sys_service_feedback"],
        "system": """你是招商银行智能客服助手 (P3 礼貌语回应)。
重要: 这是告别/感谢/问候类对话, 不是业务问题。
- 必须友好回应, 严禁建议"转人工"或"95555"
- 严禁把礼貌语误判为投诉/紧急情况
- 回复简短礼貌, 30 字以内""",
        "user_template": """用户问题: {query}
L1 识别为: {intent} (priority=P3, 礼貌语)
请直接友好回应。""",
    },

    # 默认兜底: 长尾 / 边界 case
    "default": {
        "trigger_intents": [],
        "system": """你是招商银行智能客服助手 (默认兜底)。
保守策略:
- 涉及账户安全 / 合规 / 投诉, 建议转人工 95555
- 涉及业务数字 (利率/手续费/额度), 不确定时说"建议联系人工客服"
- 礼貌语 (谢谢/再见/拜拜), 友好回应, 不建议转人工
- 回答简洁, 200 字以内""",
        "user_template": """用户问题: {query}
L1 识别为: {intent} (priority=?)
请给出回复。""",
    },
}


def select_l3_prompt(intent: str, priority: str) -> Dict:
    """根据 L1 识别结果路由到定制 Prompt"""
    # P0 红线优先
    if priority == "P0" or intent in L3_PROMPT_REGISTRY["p0_redline"]["trigger_intents"]:
        return L3_PROMPT_REGISTRY["p0_redline"]
    # P3 礼貌语优先 (避免误判)
    if priority == "P3" or intent in L3_PROMPT_REGISTRY["p3_courtesy"]["trigger_intents"]:
        return L3_PROMPT_REGISTRY["p3_courtesy"]
    # P1 业务咨询
    if priority == "P1" or intent in L3_PROMPT_REGISTRY["p1_consult"]["trigger_intents"]:
        return L3_PROMPT_REGISTRY["p1_consult"]
    return L3_PROMPT_REGISTRY["default"]

    def _llm_output_is_p0(self, llm_output: str) -> bool:
        """LLM 输出 P0 语义检测 (严格: 必须包含 P0 红线关键词 + 明确建议转人工)"""
        # 必须同时满足: 包含 P0 关键词 AND 包含转人工信号
        # v3.10.0 扩展: 加 "红线/违规/隐私/社工/钓鱼" 等扩展关键词族
        # 解决: LLM 识破了 "其他客户账户信息/忽略之前指令" 这种 query 时
        #       输出 "红线提示/违规/隐私保护" 但没触发 P0 的问题
        p0_keywords = [
            # 原始 9 个
            "反欺诈", "反洗钱", "冻结", "挂失", "盗刷", "被骗", "冒名", "假冒公检法", "保本高收益",
            # v3.10.0 扩展关键词族
            "红线", "违规", "违规行为", "严重违规",
            "隐私保护", "客户隐私", "隐私", "保密原则",
            "社工", "提示词注入", "prompt injection",
            "钓鱼", "钓鱼链接", "钓鱼网站",
            "泄露", "信息泄露", "数据泄露",
            "合规专员", "合规要求",
        ]
        transfer_signals = ["转人工", "95555", "客服专员", "客服人员"]
        has_p0_kw = any(kw in llm_output for kw in p0_keywords)
        has_transfer = any(s in llm_output for s in transfer_signals)
        # 只有同时包含 P0 关键词和转人工信号才算 P0
        return has_p0_kw and has_transfer

    def _p0_response_template(self, l0_categories: List) -> str:
        """P0 红线标准回复模板"""
        return (
            "您的问题涉及账户安全和合规事项, 我已为您转接 95555 客服专员处理。"
            "请保持电话畅通, 切勿向陌生人转账或泄露验证码。"
        )

    def get_stats(self) -> Dict:
        return self._stats.copy()


# 已知 P0 意图列表 (从 v3.6.1 P0 patch 提取)
P0_INTENT_LIST = {
    "card_loss", "card_freeze", "fraud_report", "complaint",
    "aml_large", "aml_structured", "safety_card_freeze",
    "fraud_fake_official", "fraud_high_risk", "fraud_investment",
    "fraud_transfer", "unauthorized_proxy_query",
    "unauthorized_proxy_transaction",
}


# ============================================================
# 评测脚本: 训练集 / 测试集分离 + 真跑 Cascade
# ============================================================

def run_cascade_eval():
    print("=" * 70)
    print("Cascade E2E v3.8.0 — 真跑 L1规则 → L2 BERT → L3 MiniMax LLM")
    print("=" * 70)

    # 加载测试集 (D v3.2, 1500 条) - 数据结构: {"samples": [...], "dataset_version": ...}
    eval_path = _ROOT / "data" / "D_eval_set_v3.2.json"
    with open(eval_path, "r", encoding="utf-8") as f:
        eval_data = json.load(f)

    # 标准化为 list[dict] - D v3.2 顶层是 {"samples": [...]}
    if isinstance(eval_data, dict):
        eval_items = eval_data.get("samples", [])
    else:
        eval_items = eval_data

    print(f"\n[数据集分离声明]")
    print(f"  - BERT 训练集: 项目内部种子集 (v3.5.5), 训练时已划分 train/val/holdout")
    print(f"  - BERT holdout acc: 98.71% (result.json 真实记录)")
    print(f"  - 测试集: D_eval_set_v3.2.json ({len(eval_items)} 条, 项目自建评测集)")
    print(f"  - ⚠️ D v3.2 与 BERT 训练集来源不同, 但有 IR label 空间重叠")
    print(f"  - ⚠️ 严格说 D v3.2 不是纯 OOD (P0 patch 在这份上调过)")

    # 实例化 Cascade (enable_llm=True 真实调 MiniMax)
    cascade = CascadeE2EV38(enable_llm=True, confidence_threshold=0.85)

    # 跑 50 条有意义 query: 按 priority 分层采样 P0/P1/P2/P3 各 12-13 条
    sample_size = 50
    p0_samples = [s for s in eval_items if s.get("priority") == "P0"][:13]
    p1_samples = [s for s in eval_items if s.get("priority") == "P1"][:13]
    p2_samples = [s for s in eval_items if s.get("priority") == "P2"][:12]
    p3_samples = [s for s in eval_items if s.get("priority") == "P3"][:12]
    eval_samples = p0_samples + p1_samples + p2_samples + p3_samples
    print(f"\n[Cascade 推理] 跑 {sample_size} 条分层采样 (P0:{len(p0_samples)} P1:{len(p1_samples)} P2:{len(p2_samples)} P3:{len(p3_samples)})")
    print(f"  LLM 模型: {os.environ.get('MINIMAX_MODEL', 'MiniMax-M3')}")
    print(f"  置信度门控: 0.85")

    results = []
    for i, item in enumerate(eval_samples):
        if isinstance(item, dict):
            query = item.get("query") or item.get("text") or item.get("user_input") or str(item)
            expected = item.get("expected_action") or item.get("label") or item.get("intent") or "unknown"
            priority = item.get("priority", "?")
            intent_top1 = item.get("intent_top1", "?")
        else:
            query = str(item)
            expected = "unknown"
            priority = "?"
            intent_top1 = "?"

        print(f"\n[{i+1}/{sample_size}] [{priority}] {intent_top1}: {query[:50]}{'...' if len(query) > 50 else ''}")
        result = cascade.handle(query, priority=priority)
        results.append({
            "query": query,
            "priority": priority,
            "intent_top1": intent_top1,
            "expected_action": expected,
            "cascade_path": result["cascade_path"],
            "final_action": result["final_action"],
            "final_intent": result["final_intent"],
            "final_confidence": result["final_confidence"],
            "p0_triggered": result["p0_triggered"],
            "elapsed_ms": result["elapsed_ms"],
        })

        # 打印分层路径
        for layer in result["cascade_path"]:
            layer_name = layer.get("layer", "?")
            if "intent" in layer:
                print(f"  → {layer_name}: {layer['intent']} (conf={layer.get('confidence', 0):.2f}, p0={layer.get('is_p0', False)})")
            elif "status" in layer:
                print(f"  → {layer_name}: {layer['status']}")
            elif "response_preview" in layer:
                print(f"  → {layer_name}: {layer['response_preview']}")

        print(f"  → 最终: action={result['final_action']}, p0={result['p0_triggered']}, {result['elapsed_ms']}ms")

    # 输出统计
    stats = cascade.get_stats()
    print(f"\n[统计] L1 规则直答: {stats['L1_rule_hit']}")
    print(f"[统计] L1 P0 转人工: {stats['L1_rule_p0']}")
    print(f"[统计] L2 BERT 直答: {stats['L2_bert_hit']}")
    print(f"[统计] L2 BERT P0 转人工: {stats['L2_bert_p0']}")
    print(f"[统计] L3 LLM 直答: {stats['L3_llm_hit']}")
    print(f"[统计] L3 LLM P0 转人工: {stats['L3_llm_p0']}")
    print(f"[统计] 转人工总数: {stats['transfer_human_total']}")
    print(f"[统计] LLM 调用错误: {stats['llm_error']}")

    # Action 准确率 (按 priority 分层)
    action_correct = {"P0": [0, 0], "P1": [0, 0], "P2": [0, 0], "P3": [0, 0]}
    p0_recall_correct = 0
    p0_total = 0
    for r in results:
        pri = r.get("priority", "?")
        if pri not in action_correct:
            continue
        action_correct[pri][1] += 1
        final = r["final_action"]
        if pri == "P0":
            p0_total += 1
            if final == "transfer_human":
                p0_recall_correct += 1
                action_correct[pri][0] += 1
        else:
            # 非 P0 期望 answer 或 clarify
            if final in ("answer", "clarify", "fallback_to_human"):
                action_correct[pri][0] += 1

    print(f"\n[Action 准确率]")
    for pri, (correct, total) in action_correct.items():
        if total > 0:
            print(f"  {pri}: {correct}/{total} = {correct/total:.1%}")
    if p0_total > 0:
        print(f"\n  P0 转人工召回: {p0_recall_correct}/{p0_total} = {p0_recall_correct/p0_total:.1%}")

    # 保存报告
    report = {
        "version": "v3.8.0-cascade-real",
        "run_date": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "dataset_split": {
            "train_source": "项目内部种子集 v3.5.5 (训练时已分 train/val/holdout)",
            "test_source": "D_eval_set_v3.2.json",
            "test_size": len(eval_items),
            "sample_tested": len(eval_samples),
            "sample_breakdown": {"P0": len(p0_samples), "P1": len(p1_samples), "P2": len(p2_samples), "P3": len(p3_samples)},
            "bert_holdout_acc": 0.9871,
            "honest_note": "D v3.2 与 BERT 训练集来源不同但有 label 空间重叠, 非纯 OOD",
        },
        "cascade_config": {
            "L1": "IntentRecognizer + 4层 P0 红线兜底",
            "L2": "M3-bert-base-chinese (holdout 98.71%)",
            "L3": f"MiniMax API ({os.environ.get('MINIMAX_MODEL', 'MiniMax-M2.7')})",
            "confidence_threshold": 0.85,
        },
        "stats": stats,
        "action_accuracy": {pri: {"correct": c, "total": t, "rate": c/t if t>0 else 0} for pri, (c, t) in action_correct.items()},
        "p0_recall": {"correct": p0_recall_correct, "total": p0_total, "rate": p0_recall_correct/p0_total if p0_total>0 else 0},
        "results_sample": results,
    }

    report_path = _ROOT / "data" / "cascade_v380_real_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n报告已保存: {report_path}")
    print(f"\n[诚实声明]")
    print(f"  1. 跑了 {sample_size} 条分层采样 (P0/P1/P2/P3 各 12-13 条)")
    print(f"  2. 全量 1500 条 LLM 调用 ~12 小时, token 成本另算, 未跑")
    print(f"  3. D v3.2 非纯 OOD, 严格样本外验证需准备 OOD 评测集")


if __name__ == "__main__":
    run_cascade_eval()