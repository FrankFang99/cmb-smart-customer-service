"""
可观测平台 (Observability Platform) — AI 智能客服项目
==================================================

类 LangSmith / Langfuse 设计:
- Trace: 一次完整对话的链路 (root)
- Span: 链路中的一段操作 (LL1/L2/L3/RAG/Prompt/LLM API)
- Event: Span 内的事件 (检索命中文档、规则触发、置信度等)

设计原则:
1. 0 外部依赖 (用 Python 内置 sqlite3)
2. 装饰器模式埋点 (不破坏现有代码)
3. 上下文传播 (跨函数 Span 自动嵌套)
4. Bad Case 标记 + 一键还原
5. JSON / SQLite 双写 (降级兼容)

行业对齐 (2026-06):
- LangSmith / Langfuse / Arize Phoenix 都用类似的 trace/span/event 三层结构
- OpenTelemetry 标准的 span_name / attributes / events
- 单机项目用 SQLite, 生产可换 Postgres
"""
from .trace_recorder import (
    TraceRecorder,
    TraceContext,
    SpanContext,
    trace_span,
    get_recorder,
)
from .badcase_replayer import BadCaseReplayer
from .trace_query import TraceQuery

__all__ = [
    "TraceRecorder",
    "TraceContext",
    "SpanContext",
    "trace_span",
    "get_recorder",
    "BadCaseReplayer",
    "TraceQuery",
]