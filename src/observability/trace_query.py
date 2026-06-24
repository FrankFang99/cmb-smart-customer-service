"""
Trace Query API — 查询 / 过滤 / 统计
====================================

支持:
- 按 trace_id 查完整链路
- 按 final_action / priority / p0_triggered / is_bad_case 过滤
- 按 layer / name 过滤 span
- 统计汇总 (各层耗时 / P0 召回 / LLM 调用成功率)
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from .trace_recorder import _ROOT


class TraceQuery:
    """可观测数据查询接口"""

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = _ROOT / "data" / "observability.db"
        self.db_path = Path(db_path)

    def _conn(self):
        return sqlite3.connect(str(self.db_path))

    # ============================================================
    # Trace 级别查询
    # ============================================================

    def get_trace(self, trace_id: str) -> Optional[Dict]:
        """获取单个 trace 详情"""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM traces WHERE trace_id=?", (trace_id,)
            ).fetchone()
            if not row:
                return None
            return self._row_to_trace(row)

    def list_traces(
        self,
        limit: int = 50,
        offset: int = 0,
        final_action: Optional[str] = None,
        priority: Optional[str] = None,
        p0_triggered: Optional[bool] = None,
        is_bad_case: Optional[bool] = None,
        has_error: Optional[bool] = None,
        order_by: str = "start_time DESC",
    ) -> List[Dict]:
        """列出 trace (支持多种过滤)"""
        where_clauses = []
        params: List = []
        if final_action:
            where_clauses.append("final_action = ?")
            params.append(final_action)
        if priority:
            where_clauses.append("priority = ?")
            params.append(priority)
        if p0_triggered is not None:
            where_clauses.append("p0_triggered = ?")
            params.append(1 if p0_triggered else 0)
        if is_bad_case is not None:
            where_clauses.append("is_bad_case = ?")
            params.append(1 if is_bad_case else 0)
        if has_error is True:
            where_clauses.append(
                "trace_id IN (SELECT DISTINCT trace_id FROM spans WHERE status='error')"
            )
        elif has_error is False:
            where_clauses.append(
                "trace_id NOT IN (SELECT DISTINCT trace_id FROM spans WHERE status='error')"
            )

        where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
        sql = f"SELECT * FROM traces{where_sql} ORDER BY {order_by} LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self._conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_trace(r) for r in rows]

    def count_traces(self, **filters) -> int:
        """统计 trace 数量 (支持同 list_traces 的过滤)"""
        where_clauses = []
        params: List = []
        if filters.get("final_action"):
            where_clauses.append("final_action = ?")
            params.append(filters["final_action"])
        if filters.get("priority"):
            where_clauses.append("priority = ?")
            params.append(filters["priority"])
        if filters.get("p0_triggered") is not None:
            where_clauses.append("p0_triggered = ?")
            params.append(1 if filters["p0_triggered"] else 0)
        if filters.get("is_bad_case") is not None:
            where_clauses.append("is_bad_case = ?")
            params.append(1 if filters["is_bad_case"] else 0)

        where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
        sql = f"SELECT COUNT(*) FROM traces{where_sql}"
        with self._conn() as conn:
            return conn.execute(sql, params).fetchone()[0]

    # ============================================================
    # Span 级别查询
    # ============================================================

    def get_spans(self, trace_id: str) -> List[Dict]:
        """获取一个 trace 的所有 spans (按时间排序)"""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM spans WHERE trace_id=? ORDER BY start_time ASC",
                (trace_id,),
            ).fetchall()
            return [self._row_to_span(r) for r in rows]

    def get_span_tree(self, trace_id: str) -> Dict:
        """获取一个 trace 的 span 树 (层级结构)"""
        spans = self.get_spans(trace_id)
        # 建树
        span_map = {s["span_id"]: dict(s, children=[]) for s in spans}
        root_spans = []
        for s in spans:
            parent = s.get("parent_span_id")
            if parent and parent in span_map:
                span_map[parent]["children"].append(span_map[s["span_id"]])
            else:
                root_spans.append(span_map[s["span_id"]])
        return {
            "trace_id": trace_id,
            "root_spans": root_spans,
            "total_spans": len(spans),
        }

    def get_events(self, trace_id: str) -> List[Dict]:
        """获取一个 trace 的所有 events"""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM events WHERE trace_id=? ORDER BY timestamp ASC",
                (trace_id,),
            ).fetchall()
            return [self._row_to_event(r) for r in rows]

    # ============================================================
    # 统计分析
    # ============================================================

    def layer_stats(self) -> Dict[str, Dict]:
        """按 layer 统计 (调用次数 / 平均耗时 / 错误率)"""
        sql = """
        SELECT layer,
               COUNT(*) as cnt,
               AVG(elapsed_ms) as avg_ms,
               SUM(CASE WHEN status='error' THEN 1 ELSE 0 END) as err_cnt
        FROM spans
        WHERE layer IS NOT NULL
        GROUP BY layer
        ORDER BY cnt DESC
        """
        with self._conn() as conn:
            rows = conn.execute(sql).fetchall()
            return {
                r[0]: {
                    "count": r[1],
                    "avg_elapsed_ms": round(r[2] or 0, 2),
                    "error_count": r[3],
                    "error_rate": round(r[3] / r[1], 3) if r[1] > 0 else 0,
                }
                for r in rows
            }

    def p0_recall(self) -> Dict:
        """P0 召回率统计 (在评测 priority 已知时)"""
        sql = """
        SELECT priority,
               COUNT(*) as total,
               SUM(p0_triggered) as p0_caught
        FROM traces
        WHERE priority IS NOT NULL
        GROUP BY priority
        """
        with self._conn() as conn:
            rows = conn.execute(sql).fetchall()
            return {
                r[0]: {
                    "total": r[1],
                    "p0_caught": r[2] or 0,
                    "recall_rate": round((r[2] or 0) / r[1], 3) if r[1] > 0 else 0,
                }
                for r in rows
            }

    def bad_cases(self, limit: int = 20) -> List[Dict]:
        """获取所有 Bad Case"""
        return self.list_traces(limit=limit, is_bad_case=True)

    # ============================================================
    # 内部工具
    # ============================================================

    def _row_to_trace(self, row) -> Dict:
        return {
            "trace_id": row[0],
            "user_input": row[1],
            "start_time": row[2],
            "end_time": row[3],
            "elapsed_ms": row[4],
            "final_action": row[5],
            "final_intent": row[6],
            "p0_triggered": bool(row[7]),
            "is_bad_case": bool(row[8]),
            "bad_case_reason": row[9],
            "metadata": json.loads(row[10]) if row[10] else {},
            "expected_action": row[11],
            "priority": row[12],
            "intent_top1": row[13],
            "created_at": row[14] if len(row) > 14 else None,
        }

    def _row_to_span(self, row) -> Dict:
        return {
            "span_id": row[0],
            "trace_id": row[1],
            "parent_span_id": row[2],
            "name": row[3],
            "start_time": row[4],
            "end_time": row[5],
            "elapsed_ms": row[6],
            "status": row[7],
            "attributes": json.loads(row[8]) if row[8] else {},
            "error": row[9],
            "layer": row[10],
        }

    def _row_to_event(self, row) -> Dict:
        return {
            "event_id": row[0],
            "span_id": row[1],
            "trace_id": row[2],
            "name": row[3],
            "timestamp": row[4],
            "payload": json.loads(row[5]) if row[5] else {},
        }