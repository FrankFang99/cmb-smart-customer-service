"""
Bad Case Replayer — 案发现场一键还原
====================================

解决 PM 的核心痛点: "Bad Case 出现了, 为什么?"
- 用户输入是什么?
- 检索到了哪几篇文档?
- Agent 思考的逻辑链 (L1→L2→L3 怎么走的)?
- 最终调用了哪个 API (LLM 用了什么 prompt / response)?
- 输出是什么 (为什么用户看到的是这个)?

设计:
1. 完整还原: 重建 trace 的层级调用树
2. 时间线: 每个 span 的耗时 + 开始时间
3. 关键事件高亮: P0 触发 / LLM 错误 / 检索为空 等
4. 一键导出: JSON / Markdown / HTML 报告
5. Bad Case 自动检测: action 与 expected 不符 / 错误状态 / P0 漏检
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .trace_query import TraceQuery


@dataclass
class CrimeSceneReport:
    """案发现场报告"""

    trace_id: str
    user_input: str
    priority: Optional[str]
    expected_action: Optional[str]
    final_action: str
    final_intent: Optional[str]
    p0_triggered: bool
    is_bad_case: bool
    bad_case_reason: Optional[str]
    elapsed_ms: float
    timeline: List[Dict]  # 时间线
    cascade_path: List[Dict]  # L1→L2→L3 路径
    llm_calls: List[Dict]  # LLM 完整调用
    rag_hits: List[Dict]  # 检索命中
    errors: List[Dict]  # 错误列表

    def to_dict(self) -> Dict:
        return {
            "trace_id": self.trace_id,
            "user_input": self.user_input,
            "priority": self.priority,
            "expected_action": self.expected_action,
            "final_action": self.final_action,
            "final_intent": self.final_intent,
            "p0_triggered": self.p0_triggered,
            "is_bad_case": self.is_bad_case,
            "bad_case_reason": self.bad_case_reason,
            "elapsed_ms": self.elapsed_ms,
            "timeline": self.timeline,
            "cascade_path": self.cascade_path,
            "llm_calls": self.llm_calls,
            "rag_hits": self.rag_hits,
            "errors": self.errors,
        }

    def to_markdown(self) -> str:
        """生成 Markdown 报告 (用于 PR 评论 / 飞书分享)"""
        lines = []
        lines.append(f"# 🔍 案发现场还原报告")
        lines.append(f"")
        lines.append(f"**Trace ID**: `{self.trace_id}`  ")
        lines.append(f"**用户输入**: {self.user_input}  ")
        lines.append(f"**Priority**: {self.priority or '?'}  ")
        lines.append(f"**Expected Action**: {self.expected_action or '?'}  ")
        lines.append(f"**Final Action**: `{self.final_action}`  ")
        lines.append(f"**Final Intent**: `{self.final_intent}`  ")
        lines.append(f"**P0 触发**: {'✅' if self.p0_triggered else '❌'}  ")
        lines.append(f"**Bad Case**: {'⚠️ ' + self.bad_case_reason if self.is_bad_case else '✅ 正常'}  ")
        lines.append(f"**总耗时**: {self.elapsed_ms}ms  ")
        lines.append(f"")

        # 时间线
        lines.append(f"## ⏱️ 时间线 (各层耗时)")
        lines.append(f"")
        lines.append(f"| Span | Layer | Status | 耗时 | 开始时间 |")
        lines.append(f"|------|-------|--------|------|----------|")
        for t in self.timeline:
            status_icon = {"success": "✅", "error": "❌", "running": "⏳"}.get(t["status"], "?")
            start_dt = datetime.fromtimestamp(t["start_time"]).strftime("%H:%M:%S.%f")[:-3]
            lines.append(
                f"| `{t['name']}` | {t.get('layer', '?')} | {status_icon} {t['status']} | "
                f"{t.get('elapsed_ms', 0)}ms | {start_dt} |"
            )
        lines.append(f"")

        # Cascade 路径
        if self.cascade_path:
            lines.append(f"## 🔀 Cascade 推理路径")
            lines.append(f"")
            for i, step in enumerate(self.cascade_path, 1):
                lines.append(f"### Step {i}: {step.get('layer', '?')}")
                for k, v in step.items():
                    if k == "layer":
                        continue
                    lines.append(f"- **{k}**: `{v}`")
                lines.append(f"")

        # RAG 检索
        if self.rag_hits:
            lines.append(f"## 📚 RAG 检索命中")
            lines.append(f"")
            for i, hit in enumerate(self.rag_hits, 1):
                lines.append(f"### Hit {i}: {hit.get('doc_id', '?')} (score={hit.get('score', '?')})")
                if hit.get("title"):
                    lines.append(f"**Title**: {hit['title']}  ")
                if hit.get("content_preview"):
                    lines.append(f"```")
                    lines.append(hit["content_preview"])
                    lines.append(f"```")
                lines.append(f"")

        # LLM 调用
        if self.llm_calls:
            lines.append(f"## 🧠 LLM 完整调用 ({len(self.llm_calls)} 次)")
            lines.append(f"")
            for i, call in enumerate(self.llm_calls, 1):
                lines.append(f"### Call {i}: {call.get('model', '?')} (耗时 {call.get('elapsed_ms', '?')}ms)")
                lines.append(f"**Prompt Type**: {call.get('prompt_type', '?')}  ")
                lines.append(f"**Tokens**: {call.get('tokens', '?')}  ")
                lines.append(f"")
                lines.append(f"**System Prompt**:")
                lines.append(f"```")
                lines.append(call.get("system_prompt", "")[:500])
                lines.append(f"```")
                lines.append(f"")
                lines.append(f"**User Prompt**:")
                lines.append(f"```")
                lines.append(call.get("user_prompt", "")[:500])
                lines.append(f"```")
                lines.append(f"")
                lines.append(f"**Response**:")
                lines.append(f"```")
                lines.append(call.get("response", "")[:1000])
                lines.append(f"```")
                lines.append(f"")

        # 错误
        if self.errors:
            lines.append(f"## ❌ 错误")
            lines.append(f"")
            for e in self.errors:
                lines.append(f"- `{e.get('span_name', '?')}`: {e.get('error', '?')}")

        return "\n".join(lines)


class BadCaseReplayer:
    """案发现场还原器"""

    def __init__(self, db_path: Optional[Path] = None):
        self.query = TraceQuery(db_path)

    def replay(self, trace_id: str, auto_detect_bad_case: bool = True) -> CrimeSceneReport:
        """还原一个 trace 的完整现场"""
        trace = self.query.get_trace(trace_id)
        if not trace:
            raise ValueError(f"Trace not found: {trace_id}")

        spans = self.query.get_spans(trace_id)
        events = self.query.get_events(trace_id)

        # 构造时间线
        timeline = []
        for s in spans:
            timeline.append({
                "span_id": s["span_id"],
                "name": s["name"],
                "layer": s.get("layer"),
                "start_time": s["start_time"],
                "end_time": s["end_time"],
                "elapsed_ms": s.get("elapsed_ms", 0),
                "status": s["status"],
                "attributes": s.get("attributes", {}),
            })

        # 提取 cascade path (按层级顺序)
        cascade_path = []
        for s in spans:
            layer = s.get("layer", "")
            if layer in ("L0", "L1", "L2", "L3"):
                attrs = s.get("attributes", {})
                step = {"layer": layer, "span_name": s["name"]}
                step.update({k: v for k, v in attrs.items() if k in [
                    "intent", "confidence", "is_p0", "l0_triggered",
                    "source", "fallback_reason", "status", "response_preview"
                ]})
                cascade_path.append(step)

        # 提取 LLM 调用 (从 span attributes + events)
        llm_calls = []
        for s in spans:
            attrs = s.get("attributes", {})
            layer = s.get("layer", "")
            # LLM span 判定: layer=L3 或 含 system_prompt/user_prompt/response
            is_llm_span = (
                layer == "L3"
                or "system_prompt" in attrs
                or "user_prompt" in attrs
                or "response" in attrs
                or "prompt_type" in attrs
            )
            if is_llm_span:
                llm_calls.append({
                    "span_id": s["span_id"],
                    "span_name": s["name"],
                    "model": attrs.get("model", "?"),
                    "elapsed_ms": s.get("elapsed_ms", 0),
                    "prompt_type": attrs.get("prompt_type", "?"),
                    "system_prompt": attrs.get("system_prompt", ""),
                    "user_prompt": attrs.get("user_prompt", attrs.get("prompt", "")),
                    "response": attrs.get("response", attrs.get("return_preview", "")),
                    "tokens": attrs.get("tokens", "?"),
                })

        # 提取 RAG 命中 (从 events 中 name=rag_hit / kb_hit / retrieval)
        rag_hits = []
        for e in events:
            if e["name"] in ("rag_hit", "kb_hit", "retrieval", "retrieve"):
                rag_hits.append(e["payload"])

        # 提取错误
        errors = []
        for s in spans:
            if s["status"] == "error" or s.get("error"):
                errors.append({
                    "span_id": s["span_id"],
                    "span_name": s["name"],
                    "error": s.get("error", "unknown"),
                })

        # Bad Case 自动检测
        is_bad_case = trace["is_bad_case"]
        bad_case_reason = trace["bad_case_reason"]
        if auto_detect_bad_case and not is_bad_case:
            detection = self._detect_bad_case(trace, spans, errors)
            if detection:
                is_bad_case = True
                bad_case_reason = detection

        return CrimeSceneReport(
            trace_id=trace_id,
            user_input=trace["user_input"],
            priority=trace.get("priority"),
            expected_action=trace.get("expected_action"),
            final_action=trace["final_action"],
            final_intent=trace["final_intent"],
            p0_triggered=trace["p0_triggered"],
            is_bad_case=is_bad_case,
            bad_case_reason=bad_case_reason,
            elapsed_ms=trace.get("elapsed_ms", 0),
            timeline=timeline,
            cascade_path=cascade_path,
            llm_calls=llm_calls,
            rag_hits=rag_hits,
            errors=errors,
        )

    def _detect_bad_case(self, trace: Dict, spans: List[Dict], errors: List[Dict]) -> Optional[str]:
        """自动检测 Bad Case"""
        # 1. P0 漏检
        if trace.get("priority") == "P0" and not trace["p0_triggered"]:
            return f"P0 红线漏检: priority=P0 但 final_action={trace['final_action']} (期望 transfer_human)"

        # 2. action 与期望不符
        if trace.get("expected_action") and trace["final_action"] != trace["expected_action"]:
            return f"Action 不符: 期望 {trace['expected_action']}, 实际 {trace['final_action']}"

        # 3. 有 error 但没标记
        if errors and not trace["is_bad_case"]:
            return f"链路错误未标记: {len(errors)} 个 span 处于 error 状态"

        # 4. P1/P2 误转人工 (final_action=transfer_human 但 priority 是 P1/P2)
        if trace["final_action"] == "transfer_human" and trace.get("priority") in ("P1", "P2", "P3"):
            return f"非 P0 误转人工: priority={trace.get('priority')} 但 action=transfer_human"

        return None

    def replay_batch(self, trace_ids: List[str]) -> List[CrimeSceneReport]:
        """批量还原"""
        return [self.replay(tid) for tid in trace_ids]

    def export_markdown(self, trace_id: str, output_path: Optional[Path] = None) -> Path:
        """导出 Markdown 报告"""
        report = self.replay(trace_id)
        md = report.to_markdown()
        if output_path is None:
            output_path = Path(f"data/replay_{trace_id}.md")
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(md, encoding="utf-8")
        return output_path