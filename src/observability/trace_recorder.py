"""
Trace Recorder — 核心埋点器
============================

参考 LangSmith / Langfuse / OpenTelemetry 设计:
- Trace = 一次完整请求的 root span
- Span = 有层级关系的操作段 (parent_span_id 可构成树)
- Event = Span 内的事件 (检索命中 / 规则触发 / 异常)

数据结构 (SQLite 3 表):
- traces: 顶层 trace (一次完整对话)
- spans:  所有 span (L0/L1/L2/L3/RAG/LLM/Prompt 都是 span)
- events: span 内事件 (检索命中文档 / 阈值判断 / error)

埋点方式 (3 种):
1. 装饰器: @trace_span("L3_llm_call")
2. 上下文: with TraceRecorder.span("layer", ...) as span: span.set_attr(...)
3. 直接调用: TraceRecorder.current().add_event("rag_hit", {...})

线程安全: 用 contextvars 传播当前 trace/span 上下文
"""
from __future__ import annotations

import contextvars
import functools
import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


_ROOT = Path(__file__).resolve().parents[2]


# ============================================================
# 上下文传播 (contextvars 跨协程/线程安全)
# ============================================================

_current_trace: contextvars.ContextVar[Optional["TraceContext"]] = contextvars.ContextVar(
    "current_trace", default=None
)
_current_span: contextvars.ContextVar[Optional["SpanContext"]] = contextvars.ContextVar(
    "current_span", default=None
)
_recorder_singleton: Optional["TraceRecorder"] = None


@dataclass
class SpanContext:
    """Span 运行时上下文"""

    span_id: str
    trace_id: str
    parent_span_id: Optional[str]
    name: str
    start_time: float
    end_time: Optional[float] = None
    status: str = "running"  # running / success / error
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None
    elapsed_ms: float = 0.0

    def set_attr(self, key: str, value: Any) -> None:
        """设置属性 (用于 span 内动态信息)"""
        self.attributes[key] = value

    def add_event(self, name: str, payload: Optional[Dict] = None) -> None:
        """记录 span 内事件"""
        self.events.append({
            "name": name,
            "timestamp": time.time(),
            "payload": payload or {},
        })

    def finish(self, status: str = "success", error: Optional[str] = None) -> None:
        self.end_time = time.time()
        self.elapsed_ms = round((self.end_time - self.start_time) * 1000, 2)
        self.status = status
        if error:
            self.error = error


@dataclass
class TraceContext:
    """Trace 顶层上下文"""

    trace_id: str
    user_input: str
    start_time: float
    end_time: Optional[float] = None
    final_action: Optional[str] = None
    final_intent: Optional[str] = None
    p0_triggered: bool = False
    is_bad_case: bool = False
    bad_case_reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    elapsed_ms: float = 0.0

    def mark_bad_case(self, reason: str) -> None:
        """标记为 Bad Case (用于后续还原)"""
        self.is_bad_case = True
        self.bad_case_reason = reason


# ============================================================
# SQLite Schema
# ============================================================

SCHEMA_SQL = """
-- 顶层 trace: 一次完整对话
CREATE TABLE IF NOT EXISTS traces (
    trace_id        TEXT PRIMARY KEY,
    user_input      TEXT NOT NULL,
    start_time      REAL NOT NULL,
    end_time        REAL,
    elapsed_ms      REAL,
    final_action    TEXT,
    final_intent    TEXT,
    p0_triggered    INTEGER DEFAULT 0,
    is_bad_case     INTEGER DEFAULT 0,
    bad_case_reason TEXT,
    metadata        TEXT,  -- JSON
    expected_action TEXT,  -- 评测时标注的期望 action
    priority        TEXT,  -- P0/P1/P2/P3 (评测用)
    intent_top1     TEXT,  -- 评测用
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_traces_start ON traces(start_time);
CREATE INDEX IF NOT EXISTS idx_traces_action ON traces(final_action);
CREATE INDEX IF NOT EXISTS idx_traces_p0 ON traces(p0_triggered);
CREATE INDEX IF NOT EXISTS idx_traces_badcase ON traces(is_bad_case);
CREATE INDEX IF NOT EXISTS idx_traces_priority ON traces(priority);

-- span: 链路中的一段
CREATE TABLE IF NOT EXISTS spans (
    span_id         TEXT PRIMARY KEY,
    trace_id        TEXT NOT NULL,
    parent_span_id  TEXT,
    name            TEXT NOT NULL,
    start_time      REAL NOT NULL,
    end_time        REAL,
    elapsed_ms      REAL,
    status          TEXT,  -- running / success / error
    attributes      TEXT,  -- JSON
    error           TEXT,
    layer           TEXT,  -- L0 / L1 / L2 / L3 / RAG / PROMPT / LLM_API / TOTAL (便于查询)
    FOREIGN KEY (trace_id) REFERENCES traces(trace_id)
);

CREATE INDEX IF NOT EXISTS idx_spans_trace ON spans(trace_id);
CREATE INDEX IF NOT EXISTS idx_spans_parent ON spans(parent_span_id);
CREATE INDEX IF NOT EXISTS idx_spans_name ON spans(name);
CREATE INDEX IF NOT EXISTS idx_spans_layer ON spans(layer);

-- event: span 内的事件 (检索命中 / 规则触发)
CREATE TABLE IF NOT EXISTS events (
    event_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    span_id         TEXT NOT NULL,
    trace_id        TEXT NOT NULL,
    name            TEXT NOT NULL,
    timestamp       REAL NOT NULL,
    payload         TEXT,  -- JSON
    FOREIGN KEY (span_id) REFERENCES spans(span_id)
);

CREATE INDEX IF NOT EXISTS idx_events_span ON events(span_id);
CREATE INDEX IF NOT EXISTS idx_events_trace ON events(trace_id);
CREATE INDEX IF NOT EXISTS idx_events_name ON events(name);
"""


# ============================================================
# Trace Recorder 主类
# ============================================================

class TraceRecorder:
    """可观测平台核心 Recorder"""

    def __init__(self, db_path: Optional[Path] = None, batch_size: int = 1):
        """
        Args:
            db_path: SQLite 路径, 默认 data/observability.db
            batch_size: 批量写入大小, 1 = 实时写, 10 = 性能优先
        """
        if db_path is None:
            db_path = _ROOT / "data" / "observability.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.batch_size = batch_size
        self._pending: List[Tuple[str, tuple]] = []
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.executescript(SCHEMA_SQL)
            conn.commit()

    def _execute(self, sql: str, params: tuple = ()) -> None:
        """执行 SQL, 自动 batch flush"""
        if self.batch_size > 1:
            self._pending.append((sql, params))
            if len(self._pending) >= self.batch_size:
                self._flush()
        else:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute(sql, params)
                conn.commit()

    def _flush(self) -> None:
        if not self._pending:
            return
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.executemany("INSERT OR REPLACE INTO traces VALUES (" + ",".join(["?"] * 14) + ")" if False else self._pending[0][0], self._pending[0:1] if False else [])
            # 用更稳的方式: 逐条执行
            for sql, params in self._pending:
                conn.execute(sql, params)
            conn.commit()
        self._pending.clear()

    # ============================================================
    # Trace 生命周期
    # ============================================================

    def start_trace(
        self,
        user_input: str,
        metadata: Optional[Dict] = None,
        expected_action: Optional[str] = None,
        priority: Optional[str] = None,
        intent_top1: Optional[str] = None,
    ) -> TraceContext:
        """开启一次新 trace"""
        trace_id = f"tr_{uuid.uuid4().hex[:12]}"
        ctx = TraceContext(
            trace_id=trace_id,
            user_input=user_input,
            start_time=time.time(),
            metadata=metadata or {},
        )
        # 写入 DB (初始记录, 结束时 update)
        meta_json = json.dumps(ctx.metadata, ensure_ascii=False)
        self._execute(
            """INSERT INTO traces
               (trace_id, user_input, start_time, metadata, expected_action, priority, intent_top1)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (trace_id, user_input, ctx.start_time, meta_json, expected_action, priority, intent_top1),
        )
        # 设置上下文
        _current_trace.set(ctx)
        _current_span.set(None)
        return ctx

    def finish_trace(
        self,
        ctx: TraceContext,
        final_action: str,
        final_intent: Optional[str] = None,
        p0_triggered: bool = False,
    ) -> None:
        """结束 trace, 写最终结果"""
        ctx.end_time = time.time()
        ctx.elapsed_ms = round((ctx.end_time - ctx.start_time) * 1000, 2)
        ctx.final_action = final_action
        ctx.final_intent = final_intent
        ctx.p0_triggered = p0_triggered
        meta_json = json.dumps(ctx.metadata, ensure_ascii=False)
        self._execute(
            """UPDATE traces SET
               end_time=?, elapsed_ms=?, final_action=?, final_intent=?,
               p0_triggered=?, is_bad_case=?, bad_case_reason=?, metadata=?
               WHERE trace_id=?""",
            (
                ctx.end_time, ctx.elapsed_ms, final_action, final_intent,
                1 if p0_triggered else 0, 1 if ctx.is_bad_case else 0,
                ctx.bad_case_reason, meta_json, ctx.trace_id,
            ),
        )
        # 清空上下文
        _current_trace.set(None)
        _current_span.set(None)

    # ============================================================
    # Span 生命周期
    # ============================================================

    @contextmanager
    def span(self, name: str, layer: Optional[str] = None, **attrs):
        """开启一个 span (with 语法)

        用法:
            with recorder.span("L3_llm_call", layer="L3") as s:
                s.set_attr("prompt", prompt_text)
                s.add_event("llm_response", {"tokens": 1024})
        """
        trace = _current_trace.get()
        if trace is None:
            # 没有 trace 时降级: 不记录 (避免污染), 给一个临时 ctx
            yield SpanContext(
                span_id="noop", trace_id="noop", parent_span_id=None,
                name=name, start_time=time.time(),
            )
            return

        parent = _current_span.get()
        span_id = f"sp_{uuid.uuid4().hex[:12]}"
        ctx = SpanContext(
            span_id=span_id,
            trace_id=trace.trace_id,
            parent_span_id=parent.span_id if parent else None,
            name=name,
            start_time=time.time(),
            attributes=dict(attrs),
            # 推断 layer
        )
        # layer 默认从 name 前缀推断 (L0/L1/L2/L3/RAG/PROMPT/LLM_API)
        inferred_layer = layer or _infer_layer(name)
        # 写入 DB
        self._execute(
            """INSERT INTO spans
               (span_id, trace_id, parent_span_id, name, start_time, layer, attributes, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                span_id, trace.trace_id,
                ctx.parent_span_id, name, ctx.start_time,
                inferred_layer, json.dumps(ctx.attributes, ensure_ascii=False),
                "running",
            ),
        )

        # 设为当前 span (嵌套)
        token = _current_span.set(ctx)
        try:
            yield ctx
            ctx.finish(status="success")
        except Exception as e:
            ctx.finish(status="error", error=str(e)[:500])
            raise
        finally:
            # 写入最终状态
            attrs_json = json.dumps(ctx.attributes, ensure_ascii=False)
            self._execute(
                """UPDATE spans SET
                   end_time=?, elapsed_ms=?, status=?, attributes=?, error=?
                   WHERE span_id=?""",
                (
                    ctx.end_time, ctx.elapsed_ms, ctx.status, attrs_json,
                    ctx.error, span_id,
                ),
            )
            # 把 events 写入
            for ev in ctx.events:
                self._execute(
                    """INSERT INTO events
                       (span_id, trace_id, name, timestamp, payload)
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        span_id, trace.trace_id, ev["name"], ev["timestamp"],
                        json.dumps(ev["payload"], ensure_ascii=False),
                    ),
                )
            # 恢复父 span
            _current_span.reset(token)

    def add_event(self, name: str, payload: Optional[Dict] = None) -> None:
        """在当前 span 内追加 event (不进 span 上下文也能用)"""
        span = _current_span.get()
        if span is None or span.span_id == "noop":
            return
        span.add_event(name, payload)
        trace = _current_trace.get()
        self._execute(
            """INSERT INTO events
               (span_id, trace_id, name, timestamp, payload)
               VALUES (?, ?, ?, ?, ?)""",
            (
                span.span_id, trace.trace_id, name, time.time(),
                json.dumps(payload or {}, ensure_ascii=False),
            ),
        )

    def set_attr(self, key: str, value: Any) -> None:
        """在当前 span 上设置属性"""
        span = _current_span.get()
        if span is None or span.span_id == "noop":
            return
        span.set_attr(key, value)
        # 同步更新 DB (attributes 是 JSON 字段, 整体覆盖)
        attrs_json = json.dumps(span.attributes, ensure_ascii=False)
        self._execute(
            "UPDATE spans SET attributes=? WHERE span_id=?",
            (attrs_json, span.span_id),
        )

    def get_current_trace(self) -> Optional[TraceContext]:
        return _current_trace.get()

    def get_current_span(self) -> Optional[SpanContext]:
        return _current_span.get()


def _infer_layer(name: str) -> str:
    """从 span name 推断 layer (用于快速过滤)"""
    name_lower = name.lower()
    if name_lower.startswith("l0_") or "l0_dict" in name_lower or "redline" in name_lower:
        return "L0"
    if name_lower.startswith("l1_") or "intent_recognize" in name_lower:
        return "L1"
    if name_lower.startswith("l2_") or "bert" in name_lower:
        return "L2"
    if name_lower.startswith("l3_") or "llm" in name_lower or "llm_api" in name_lower:
        return "L3"
    if "rag" in name_lower or "retriev" in name_lower or "kb_search" in name_lower:
        return "RAG"
    if "prompt" in name_lower or "select_l3" in name_lower:
        return "PROMPT"
    if "cascade" in name_lower or "total" in name_lower:
        return "TOTAL"
    return "OTHER"


# ============================================================
# 全局单例 + 装饰器
# ============================================================

def get_recorder(db_path: Optional[Path] = None) -> TraceRecorder:
    """获取全局 Recorder 单例"""
    global _recorder_singleton
    if _recorder_singleton is None:
        _recorder_singleton = TraceRecorder(db_path=db_path)
    return _recorder_singleton


def trace_span(name: Optional[str] = None, layer: Optional[str] = None):
    """装饰器: 自动记录整个函数的 span

    用法:
        @trace_span("L3_llm_call", layer="L3")
        def call_llm(prompt):
            ...
    """
    def decorator(func):
        span_name = name or func.__name__
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            recorder = get_recorder()
            with recorder.span(span_name, layer=layer) as s:
                s.set_attr("args_repr", _safe_repr(args))
                s.set_attr("kwargs_repr", _safe_repr(kwargs))
                result = func(*args, **kwargs)
                # 尝试记录返回值预览
                if isinstance(result, str):
                    s.set_attr("return_preview", result[:200] + ("..." if len(result) > 200 else ""))
                else:
                    s.set_attr("return_type", type(result).__name__)
                return result
        return wrapper
    return decorator


def _safe_repr(obj: Any, max_len: int = 100) -> str:
    """安全 repr (避免超长字符串)"""
    try:
        s = repr(obj)
        if len(s) > max_len:
            return s[:max_len] + "..."
        return s
    except Exception:
        return f"<unreprable {type(obj).__name__}>"