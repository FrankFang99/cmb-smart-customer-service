"""
v3.4.0 Badcase 标注池
=====================

设计目标（对标 B 站亚慧 AI 产品经理视频"Bad Case 闭环"建议）:

1. 失败样本自动入池 (JSONL, git 友好)
2. PM / 运营人员可标注:
   - 根因分类 (intent / retrieval / l0 / compliance / template)
   - 修复动作 (add_faq / adjust_threshold / transfer / ignore)
3. 一键入知识库: 标注完调 add_faq() 进 KB
4. 周会分析: 复盘哪些根因占比高 -> 下迭代重点

使用方法:
    from src.eval.badcase_pool import BadcasePool

    pool = BadcasePool()                # 默认 data/badcase/pool_v340.jsonl
    pool.add_from_eval_results(...)     # 从 eval_results_v340.json 入池
    pool.label_badcase(sample_id, root_cause, fix_action, fix_note)
    pool.add_faq_to_kb(sample_id, new_answer)  # 一键入知识库
    pool.weekly_summary()                # 周会分析
"""

from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


# 根因分类
ROOT_CAUSE_OPTIONS = [
    "intent_mismatch",    # 意图识别错
    "retrieval_miss",     # 检索没召回
    "l0_false_trigger",   # L0 误触发 (P0 误判)
    "l0_miss_trigger",    # L0 漏触发 (P0 漏判)
    "compliance_violation",  # 合规话术缺失
    "template_poor",      # 模板质量差
    "cascade_routing_err",  # cascade 路由错误
    "kb_outdated",        # 知识过期
    "unknown",            # 待人工分析
]

# 修复动作
FIX_ACTION_OPTIONS = [
    "add_faq",            # 加 FAQ 到知识库
    "adjust_threshold",   # 调阈值 (意图置信 / 模板置信)
    "add_intent_pattern", # 加意图模式 (rules)
    "transfer_to_human",  # 强转人工
    "ignore",             # 边界 case 忽略
    "pending",            # 待定
]

# 严重等级
P_LEVEL = {
    "P0": 0,  # 24h 内修复 (合规/金钱损失/多人反馈)
    "P1": 1,  # 3d 修复 (单条错误/重要幻觉)
    "P2": 2,  # 1w 修复 (边界/主观差异)
}


class BadcaseRecord:
    """单条 Badcase 记录"""

    def __init__(
        self,
        sample_id: str,
        question: str,
        expected_intent: str,
        actual_intent: str,
        is_p0_label: bool,
        l0_triggered: bool,
        cascade: str,
        action: str,
        elapsed_ms: float,
        llm_called: bool,
        rag_hit: bool,
        intent_match: bool,
        transfer_correct: bool,
        p0_recall: Optional[bool],
        l0_compliance: Optional[bool],
        # 标注字段 (PM 填)
        root_cause: str = "unknown",
        fix_action: str = "pending",
        p_level: str = "P2",
        fix_note: str = "",
        fix_done: bool = False,
        # 元数据
        eval_version: str = "v3.4.0",
        eval_date: str = "",
        created_at: str = "",
        updated_at: str = "",
    ):
        self.sample_id = sample_id
        self.question = question
        self.expected_intent = expected_intent
        self.actual_intent = actual_intent
        self.is_p0_label = is_p0_label
        self.l0_triggered = l0_triggered
        self.cascade = cascade
        self.action = action
        self.elapsed_ms = elapsed_ms
        self.llm_called = llm_called
        self.rag_hit = rag_hit
        self.intent_match = intent_match
        self.transfer_correct = transfer_correct
        self.p0_recall = p0_recall
        self.l0_compliance = l0_compliance
        self.root_cause = root_cause
        self.fix_action = fix_action
        self.p_level = p_level
        self.fix_note = fix_note
        self.fix_done = fix_done
        self.eval_version = eval_version
        self.eval_date = eval_date
        now = datetime.now().isoformat(timespec="seconds")
        self.created_at = created_at or now
        self.updated_at = updated_at or now

    @staticmethod
    def _auto_p_level(rec: Dict[str, Any]) -> str:
        """根据评测字段自动定级"""
        if rec.get("l0_compliance") is False:
            return "P0"
        if rec.get("is_p0_label") and rec.get("p0_recall") is False:
            return "P0"
        if rec.get("expected_intent", "").startswith("sec_") and not rec.get("intent_match", True):
            return "P0"
        if not rec.get("intent_match", True):
            return "P1"
        return "P2"

    @staticmethod
    def _auto_root_cause(rec: Dict[str, Any]) -> str:
        """根据评测字段自动初判根因"""
        if not rec.get("intent_match", True):
            return "intent_mismatch"
        if rec.get("is_p0_label") and rec.get("p0_recall") is False:
            return "l0_miss_trigger"
        if rec.get("l0_triggered") and not rec.get("expected_intent", "").startswith("sec_") and \
           not rec.get("expected_intent", "").startswith("cons_urg_") and \
           not rec.get("expected_intent", "").startswith("cons_comp_"):
            return "l0_false_trigger"
        if not rec.get("rag_hit", True):
            return "retrieval_miss"
        if rec.get("cascade") == "?":
            return "cascade_routing_err"
        return "unknown"

    @classmethod
    def from_eval_sample(cls, sample: Dict[str, Any]) -> "BadcaseRecord":
        rec = cls(
            sample_id=sample.get("sample_id", "UNKNOWN"),
            question=sample.get("question", ""),
            expected_intent=sample.get("expected_intent", ""),
            actual_intent=sample.get("actual_intent", ""),
            is_p0_label=sample.get("is_p0_label", False),
            l0_triggered=sample.get("l0_triggered", False),
            cascade=sample.get("cascade", "?"),
            action=sample.get("action", ""),
            elapsed_ms=sample.get("elapsed_ms", 0.0),
            llm_called=sample.get("llm_called", False),
            rag_hit=sample.get("rag_hit", True),
            intent_match=sample.get("intent_match", True),
            transfer_correct=sample.get("transfer_correct", False),
            p0_recall=sample.get("p0_recall"),
            l0_compliance=sample.get("l0_compliance"),
            eval_date=sample.get("eval_date", ""),
        )
        rec.p_level = cls._auto_p_level(sample)
        rec.root_cause = cls._auto_root_cause(sample)
        return rec

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sample_id": self.sample_id,
            "question": self.question,
            "expected_intent": self.expected_intent,
            "actual_intent": self.actual_intent,
            "is_p0_label": self.is_p0_label,
            "l0_triggered": self.l0_triggered,
            "cascade": self.cascade,
            "action": self.action,
            "elapsed_ms": self.elapsed_ms,
            "llm_called": self.llm_called,
            "rag_hit": self.rag_hit,
            "intent_match": self.intent_match,
            "transfer_correct": self.transfer_correct,
            "p0_recall": self.p0_recall,
            "l0_compliance": self.l0_compliance,
            "root_cause": self.root_cause,
            "fix_action": self.fix_action,
            "p_level": self.p_level,
            "fix_note": self.fix_note,
            "fix_done": self.fix_done,
            "eval_version": self.eval_version,
            "eval_date": self.eval_date,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "BadcaseRecord":
        return cls(**d)


class BadcasePool:
    """Badcase 标注池 - JSONL 持久化"""

    def __init__(self, pool_path: Optional[str] = None):
        if pool_path is None:
            # 默认: 项目根 / data / badcase / pool_v340.jsonl
            project_root = Path(__file__).resolve().parents[2]
            self.pool_path = project_root / "data" / "badcase" / "pool_v340.jsonl"
        else:
            self.pool_path = Path(pool_path)
        self.pool_path.parent.mkdir(parents=True, exist_ok=True)
        self.records: List[BadcaseRecord] = []
        self._load()

    def _load(self):
        if not self.pool_path.exists():
            return
        with open(self.pool_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    self.records.append(BadcaseRecord.from_dict(d))
                except Exception:
                    pass

    def _save(self):
        with open(self.pool_path, "w", encoding="utf-8") as f:
            for rec in self.records:
                f.write(json.dumps(rec.to_dict(), ensure_ascii=False) + "\n")

    # ============================================================
    # 入池
    # ============================================================
    def add_from_eval_results(self, eval_results_path: str, only_failures: bool = True) -> int:
        """
        从 eval_results_v340.json 读失败样本, 入池
        Returns: 新增条数
        """
        with open(eval_results_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        samples = data.get("sample_results", [])
        existing_ids = {r.sample_id for r in self.records}
        added = 0
        for s in samples:
            if only_failures and s.get("intent_match", True) and \
               (s.get("p0_recall") is not False) and \
               (s.get("l0_compliance") is not False):
                continue
            sid = s.get("sample_id", "UNKNOWN")
            if sid in existing_ids:
                continue
            rec = BadcaseRecord.from_eval_sample(s)
            rec.eval_date = data.get("eval_date", "")
            self.records.append(rec)
            added += 1
        self._save()
        return added

    def add(self, rec: BadcaseRecord) -> bool:
        """手动加一条, 已存在则跳过"""
        if rec.sample_id in {x.sample_id for x in self.records}:
            return False
        self.records.append(rec)
        self._save()
        return True

    # ============================================================
    # 标注
    # ============================================================
    def label_badcase(
        self,
        sample_id: str,
        root_cause: str = None,
        fix_action: str = None,
        p_level: str = None,
        fix_note: str = None,
        fix_done: bool = None,
    ) -> bool:
        """标注一条 badcase (PM 操作)"""
        for rec in self.records:
            if rec.sample_id == sample_id:
                if root_cause is not None:
                    rec.root_cause = root_cause
                if fix_action is not None:
                    rec.fix_action = fix_action
                if p_level is not None:
                    rec.p_level = p_level
                if fix_note is not None:
                    rec.fix_note = fix_note
                if fix_done is not None:
                    rec.fix_done = fix_done
                rec.updated_at = datetime.now().isoformat(timespec="seconds")
                self._save()
                return True
        return False

    def get_by_p_level(self, p_level: str) -> List[BadcaseRecord]:
        return [r for r in self.records if r.p_level == p_level]

    def get_unlabeled(self) -> List[BadcaseRecord]:
        return [r for r in self.records if r.fix_action == "pending"]

    def get_open(self) -> List[BadcaseRecord]:
        return [r for r in self.records if not r.fix_done]

    # ============================================================
    # 一键入知识库
    # ============================================================
    def add_faq_to_kb(self, sample_id: str, new_answer: str, domain: str = "service") -> bool:
        """
        把标注好的 badcase 转为 FAQ, 入知识库
        实际改 knowledge_base.py 的 KNOWLEDGE_BASE 列表
        """
        target = None
        for rec in self.records:
            if rec.sample_id == sample_id:
                target = rec
                break
        if target is None:
            return False
        if target.fix_action != "add_faq":
            return False
        # 生成新 ID
        new_id = f"KB_BC_{datetime.now().strftime('%Y%m%d')}_{sample_id[-4:]}"
        new_entry = {
            "id": new_id,
            "category": "consult",
            "domain": domain,
            "domain_zh": "服务与反馈",
            "sub_category": "badcase_fix",
            "question": target.question,
            "answer": new_answer,
            "tags": ["badcase", f"from_{target.eval_version}"],
            "metadata": {
                "intent": target.expected_intent,
                "frequency": "high",  # 失败过 = 高频关注
                "risk_disclosure": False,
                "version": "v3.4.0-badcase",
            },
        }
        # 写入 KB (运行时 dict 追加, 不改源文件)
        try:
            from src.rag.knowledge_base import KNOWLEDGE_BASE
            KNOWLEDGE_BASE.append(new_entry)
        except Exception as e:
            return False
        target.fix_done = True
        target.updated_at = datetime.now().isoformat(timespec="seconds")
        self._save()
        return True

    # ============================================================
    # 周会分析
    # ============================================================
    def weekly_summary(self) -> Dict[str, Any]:
        """
        周会分析: 哪些根因占比高 -> 下一迭代重点
        """
        if not self.records:
            return {
                "total": 0,
                "by_root_cause": {},
                "by_fix_action": {},
                "by_p_level": {},
                "by_intent_group": {},
                "fix_done_count": 0,
                "fix_done_rate": 0.0,
                "p0_open_count": 0,
                "p1_open_count": 0,
                "p0_open_samples": [],
                "p1_open_samples": [],
            }
        # 根因分布
        cause_counter = Counter(r.root_cause for r in self.records)
        # 修复动作分布
        fix_counter = Counter(r.fix_action for r in self.records)
        # P 等级分布
        p_counter = Counter(r.p_level for r in self.records)
        # 完成率
        done = sum(1 for r in self.records if r.fix_done)
        # 按业务分组
        by_intent: Dict[str, int] = {}
        for r in self.records:
            grp = r.expected_intent.split("_")[0] if r.expected_intent else "unknown"
            by_intent[grp] = by_intent.get(grp, 0) + 1
        # 优先级 (P0 待办)
        p0_open = [r.sample_id for r in self.records if r.p_level == "P0" and not r.fix_done]
        p1_open = [r.sample_id for r in self.records if r.p_level == "P1" and not r.fix_done]
        return {
            "total": len(self.records),
            "by_root_cause": dict(cause_counter.most_common()),
            "by_fix_action": dict(fix_counter.most_common()),
            "by_p_level": dict(p_counter.most_common()),
            "by_intent_group": by_intent,
            "fix_done_count": done,
            "fix_done_rate": round(done / len(self.records), 3) if self.records else 0,
            "p0_open_count": len(p0_open),
            "p1_open_count": len(p1_open),
            "p0_open_samples": p0_open[:10],  # 最多列 10 条
            "p1_open_samples": p1_open[:10],
        }

    def export_markdown(self, output_path: Optional[str] = None) -> str:
        """导出为 markdown 周报"""
        summary = self.weekly_summary()
        lines = [
            "# Badcase 标注池周报 (v3.4.0)",
            f"\n> 生成时间: {datetime.now().isoformat(timespec='seconds')}\n",
            "## 概览",
            f"- 总数: {summary['total']}",
            f"- 已修复: {summary['fix_done_count']} ({summary['fix_done_rate']*100:.1f}%)",
            f"- 待修复 P0: {summary['p0_open_count']}",
            f"- 待修复 P1: {summary['p1_open_count']}",
            "\n## 根因分布",
        ]
        for cause, cnt in summary["by_root_cause"].items():
            lines.append(f"- {cause}: {cnt}")
        lines.append("\n## 修复动作分布")
        for fix, cnt in summary["by_fix_action"].items():
            lines.append(f"- {fix}: {cnt}")
        lines.append("\n## P 等级分布")
        for p, cnt in summary["by_p_level"].items():
            lines.append(f"- {p}: {cnt}")
        lines.append("\n## P0 待办 Top 10")
        for sid in summary["p0_open_samples"]:
            lines.append(f"- {sid}")
        lines.append("\n## P1 待办 Top 10")
        for sid in summary["p1_open_samples"]:
            lines.append(f"- {sid}")
        lines.append("\n## 详细记录\n")
        for r in self.records:
            lines.append(
                f"### {r.sample_id} [{r.p_level}] ({'已修复' if r.fix_done else '待修'})\n"
                f"- 问题: {r.question}\n"
                f"- 期望意图: `{r.expected_intent}`\n"
                f"- 实际意图: `{r.actual_intent}`\n"
                f"- 根因: {r.root_cause}\n"
                f"- 修复: {r.fix_action}\n"
                f"- 备注: {r.fix_note or '-'}\n"
            )
        text = "\n".join(lines)
        if output_path:
            out = Path(output_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(text, encoding="utf-8")
        return text


# ============================================================
# CLI
# ============================================================
if __name__ == "__main__":
    import sys
    pool = BadcasePool()
    print(f"Pool: {pool.pool_path}")
    print(f"Records: {len(pool.records)}")
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "import":
            eval_path = sys.argv[2] if len(sys.argv) > 2 else "data/eval_results_v340.json"
            added = pool.add_from_eval_results(eval_path, only_failures=True)
            print(f"Imported {added} new badcases from {eval_path}")
        elif cmd == "summary":
            print(json.dumps(pool.weekly_summary(), ensure_ascii=False, indent=2))
        elif cmd == "export":
            out = sys.argv[2] if len(sys.argv) > 2 else "data/badcase/weekly_report.md"
            text = pool.export_markdown(out)
            print(f"Exported to {out}")
        else:
            print("Usage: python -m src.eval.badcase_pool [import|summary|export]")
