"""
Trace Viewer Server — LangSmith 风格 UI
========================================

启动本地 HTTP server, 提供:
- /         → LangSmith 风格 HTML UI (单页应用)
- /api/traces         → trace 列表 (支持过滤)
- /api/traces/<id>    → 单个 trace 详情 + span tree + events
- /api/stats          → 各层统计 + P0 召回
- /api/badcases       → Bad Case 列表
- /api/replay/<id>    → 案发现场还原 Markdown

用法:
    python src/observability/viewer_server.py --port 8765
    浏览器打开 http://localhost:8765
"""
from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.observability.trace_query import TraceQuery
from src.observability.badcase_replayer import BadCaseReplayer


# ============================================================
# HTML UI (LangSmith 风格)
# ============================================================

INDEX_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>AI 智能客服 — Trace Viewer (类 LangSmith)</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
  background: #f8f9fb; color: #1a1a1a;
  display: flex; height: 100vh; overflow: hidden;
}
/* === 左侧: Trace 列表 === */
.left-panel {
  width: 380px; background: white; border-right: 1px solid #e1e4e8;
  display: flex; flex-direction: column;
}
.left-header {
  padding: 16px; border-bottom: 1px solid #e1e4e8;
  background: #fafbfc;
}
.left-header h1 {
  font-size: 16px; font-weight: 600; margin-bottom: 8px;
  display: flex; align-items: center; gap: 8px;
}
.left-header .stats {
  font-size: 12px; color: #586069;
}
.filters {
  padding: 12px 16px; border-bottom: 1px solid #e1e4e8;
  display: flex; flex-wrap: wrap; gap: 6px;
}
.filter-btn {
  padding: 4px 10px; border: 1px solid #d0d7de; border-radius: 12px;
  background: white; font-size: 11px; cursor: pointer;
  transition: all 0.15s;
}
.filter-btn:hover { background: #f6f8fa; }
.filter-btn.active { background: #0969da; color: white; border-color: #0969da; }
.filter-btn.bad-case { color: #cf222e; border-color: #cf222e; }
.filter-btn.bad-case.active { background: #cf222e; color: white; }
.trace-list { flex: 1; overflow-y: auto; }
.trace-item {
  padding: 12px 16px; border-bottom: 1px solid #f0f3f6;
  cursor: pointer; transition: background 0.1s;
  border-left: 3px solid transparent;
}
.trace-item:hover { background: #f6f8fa; }
.trace-item.selected { background: #ddf4ff; border-left-color: #0969da; }
.trace-item.bad-case { border-left-color: #cf222e; background: #fff5f5; }
.trace-item.bad-case.selected { background: #ffd7d5; }
.trace-item .query {
  font-size: 13px; line-height: 1.4;
  margin-bottom: 6px;
  overflow: hidden; text-overflow: ellipsis;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
}
.trace-item .meta {
  display: flex; gap: 8px; font-size: 11px; color: #586069;
  align-items: center;
}
.badge {
  display: inline-block; padding: 1px 6px; border-radius: 4px;
  font-size: 10px; font-weight: 600;
}
.badge-p0 { background: #ffebe9; color: #cf222e; }
.badge-p1 { background: #ddf4ff; color: #0969da; }
.badge-p2 { background: #fff8c5; color: #9a6700; }
.badge-p3 { background: #dafbe1; color: #1a7f37; }
.badge-action { background: #eaeef2; color: #57606a; }
.badge-action.transfer_human { background: #ffebe9; color: #cf222e; }
.badge-action.answer { background: #dafbe1; color: #1a7f37; }
.badge-bad { background: #cf222e; color: white; }

/* === 右侧: Trace 详情 === */
.right-panel {
  flex: 1; overflow-y: auto; padding: 24px;
}
.empty {
  display: flex; align-items: center; justify-content: center;
  height: 100%; color: #8b949e; font-size: 14px;
}
.detail-header {
  background: white; border: 1px solid #e1e4e8;
  border-radius: 8px; padding: 20px; margin-bottom: 16px;
}
.detail-header h2 {
  font-size: 18px; margin-bottom: 12px;
}
.detail-header .user-input {
  background: #f6f8fa; padding: 12px; border-radius: 6px;
  font-family: monospace; font-size: 13px;
  border-left: 3px solid #0969da;
  margin-bottom: 12px;
}
.meta-grid {
  display: grid; grid-template-columns: repeat(4, 1fr);
  gap: 12px; font-size: 12px;
}
.meta-cell { padding: 8px; background: #f6f8fa; border-radius: 4px; }
.meta-cell .label { color: #586069; font-size: 11px; margin-bottom: 2px; }
.meta-cell .value { font-weight: 600; }

/* === 时间线 / Span Tree === */
.timeline {
  background: white; border: 1px solid #e1e4e8;
  border-radius: 8px; padding: 20px;
}
.timeline h3 {
  font-size: 14px; margin-bottom: 16px;
  display: flex; justify-content: space-between; align-items: center;
}
.span-row {
  display: flex; align-items: flex-start; padding: 8px 0;
  border-bottom: 1px solid #f0f3f6; cursor: pointer;
}
.span-row:hover { background: #f6f8fa; }
.span-row.error { background: #fff5f5; }
.span-toggle {
  width: 16px; text-align: center; color: #586069;
  user-select: none; font-size: 10px;
}
.span-bar {
  height: 6px; border-radius: 3px; margin: 0 8px;
  flex-shrink: 0; align-self: center;
}
.span-name { flex: 0 0 200px; font-family: monospace; font-size: 12px; }
.span-layer {
  display: inline-block; padding: 1px 6px; border-radius: 3px;
  font-size: 10px; font-weight: 600; margin-left: 4px;
}
.span-layer.L0 { background: #cf222e; color: white; }
.span-layer.L1 { background: #0969da; color: white; }
.span-layer.L2 { background: #8250df; color: white; }
.span-layer.L3 { background: #1a7f37; color: white; }
.span-layer.RAG { background: #9a6700; color: white; }
.span-layer.PROMPT { background: #6e7781; color: white; }
.span-layer.TOTAL { background: #1f2328; color: white; }
.span-elapsed { font-size: 11px; color: #586069; min-width: 60px; }
.span-status { font-size: 11px; min-width: 50px; }
.span-children {
  margin-left: 20px; padding-left: 12px;
  border-left: 2px solid #e1e4e8;
  width: 100%;
}
.span-detail {
  background: #f6f8fa; padding: 12px; border-radius: 6px;
  margin: 8px 0; font-size: 12px;
  font-family: monospace; white-space: pre-wrap;
  word-break: break-all;
}
.span-detail h4 {
  font-size: 11px; color: #586069; margin: 8px 0 4px;
  font-family: -apple-system, sans-serif;
}
.section {
  margin-bottom: 16px; padding: 16px;
  background: white; border: 1px solid #e1e4e8;
  border-radius: 8px;
}
.section h3 { font-size: 14px; margin-bottom: 12px; }
.event-item {
  padding: 8px; background: #f6f8fa; border-radius: 4px;
  margin-bottom: 6px; font-size: 12px; font-family: monospace;
}
.event-name { color: #0969da; font-weight: 600; }
.llm-call {
  background: #f6f8fa; padding: 12px; border-radius: 6px;
  margin-bottom: 12px;
}
.llm-call h4 {
  font-size: 13px; margin-bottom: 8px;
  display: flex; justify-content: space-between;
}
.llm-prompt {
  background: white; padding: 10px; border-radius: 4px;
  font-family: monospace; font-size: 11px;
  white-space: pre-wrap; max-height: 200px; overflow-y: auto;
  border: 1px solid #e1e4e8;
  margin-bottom: 8px;
}
.llm-response {
  background: #dafbe1; padding: 10px; border-radius: 4px;
  font-family: monospace; font-size: 11px;
  white-space: pre-wrap; border: 1px solid #1a7f37;
}
.rag-hit {
  background: #f6f8fa; padding: 8px; border-radius: 4px;
  margin-bottom: 6px; font-size: 12px;
}
.rag-hit .doc-id { color: #0969da; font-weight: 600; }
.refresh-btn {
  padding: 4px 12px; border: 1px solid #d0d7de;
  background: white; border-radius: 4px; cursor: pointer;
  font-size: 12px;
}
.refresh-btn:hover { background: #f6f8fa; }
.crime-scene-btn {
  padding: 6px 12px; background: #cf222e; color: white;
  border: none; border-radius: 4px; cursor: pointer;
  font-size: 12px; margin-top: 12px;
}
.crime-scene-btn:hover { background: #a40e26; }
.modal-bg {
  position: fixed; top: 0; left: 0; width: 100%; height: 100%;
  background: rgba(0,0,0,0.5); display: none;
  align-items: center; justify-content: center; z-index: 1000;
}
.modal {
  background: white; padding: 24px; border-radius: 8px;
  max-width: 80%; max-height: 80%; overflow: auto;
}
</style>
</head>
<body>
<div class="left-panel">
  <div class="left-header">
    <h1>🔍 Trace Viewer <span style="font-size:10px;color:#8b949e;font-weight:400">类 LangSmith</span></h1>
    <div class="stats" id="stats">加载中...</div>
  </div>
  <div class="filters">
    <button class="filter-btn active" data-filter="all">全部</button>
    <button class="filter-btn" data-filter="p0">🔴 P0</button>
    <button class="filter-btn bad-case" data-filter="badcase">⚠️ Bad Case</button>
    <button class="filter-btn" data-filter="answer">✅ 答</button>
    <button class="filter-btn" data-filter="transfer">📞 转人工</button>
    <button class="filter-btn" data-filter="error">❌ Error</button>
  </div>
  <div class="trace-list" id="trace-list"></div>
</div>

<div class="right-panel" id="right-panel">
  <div class="empty">← 选择左侧一条 trace 查看链路</div>
</div>

<div class="modal-bg" id="modal-bg" onclick="if(event.target===this)closeModal()">
  <div class="modal" id="modal-content"></div>
</div>

<script>
const state = { filter: 'all', selectedTraceId: null, traces: [], detail: null };

async function loadStats() {
  const r = await fetch('/api/stats');
  const s = await r.json();
  document.getElementById('stats').innerHTML =
    `总 <b>${s.total_traces}</b> 条 | P0 召回 <b>${(s.p0_recall.P0?.recall_rate*100||0).toFixed(1)}%</b> | ` +
    `Bad Case <b style="color:#cf222e">${s.bad_cases_count}</b> | ` +
    `<button class="refresh-btn" onclick="loadTraces()">🔄 刷新</button>`;
}

async function loadTraces() {
  const url = '/api/traces?limit=100&' + (
    state.filter === 'p0' ? 'p0_triggered=true' :
    state.filter === 'badcase' ? 'is_bad_case=true' :
    state.filter === 'answer' ? 'final_action=answer' :
    state.filter === 'transfer' ? 'final_action=transfer_human' :
    state.filter === 'error' ? 'has_error=true' : ''
  );
  const r = await fetch(url);
  state.traces = await r.json();
  renderTraceList();
}

function renderTraceList() {
  const list = document.getElementById('trace-list');
  list.innerHTML = state.traces.map(t => `
    <div class="trace-item ${t.is_bad_case ? 'bad-case' : ''} ${t.trace_id === state.selectedTraceId ? 'selected' : ''}"
         onclick="selectTrace('${t.trace_id}')">
      <div class="query">${escapeHtml(t.user_input)}</div>
      <div class="meta">
        <span class="badge badge-${t.priority || 'p3'}">${t.priority || '?'}</span>
        <span class="badge badge-action ${t.final_action}">${t.final_action}</span>
        ${t.p0_triggered ? '<span class="badge badge-p0">P0✓</span>' : ''}
        ${t.is_bad_case ? '<span class="badge badge-bad">⚠️BAD</span>' : ''}
        <span style="color:#8b949e">${(t.elapsed_ms||0).toFixed(0)}ms · ${t.intent_top1||'?'}</span>
      </div>
    </div>
  `).join('');
}

async function selectTrace(traceId) {
  state.selectedTraceId = traceId;
  renderTraceList();
  const r = await fetch(`/api/traces/${traceId}`);
  state.detail = await r.json();
  renderDetail();
}

function renderDetail() {
  const d = state.detail;
  if (!d) return;
  const t = d.trace;
  const tree = d.span_tree;

  // 时间线最大耗时用于 bar 宽度
  const maxMs = Math.max(...tree.root_spans.flatMap(s => collectSpans(s)).map(s => s.elapsed_ms || 0), 1);

  let html = `
    <div class="detail-header">
      <h2>${t.user_input} ${t.is_bad_case ? '<span class="badge badge-bad">⚠️ BAD CASE</span>' : ''}</h2>
      <div class="user-input">${escapeHtml(t.user_input)}</div>
      <div class="meta-grid">
        <div class="meta-cell"><div class="label">Trace ID</div><div class="value" style="font-family:monospace;font-size:11px">${t.trace_id}</div></div>
        <div class="meta-cell"><div class="label">Final Action</div><div class="value">${t.final_action}</div></div>
        <div class="meta-cell"><div class="label">Intent</div><div class="value">${t.final_intent||'?'}</div></div>
        <div class="meta-cell"><div class="label">总耗时</div><div class="value">${(t.elapsed_ms||0).toFixed(1)} ms</div></div>
        <div class="meta-cell"><div class="label">Priority</div><div class="value">${t.priority||'?'}</div></div>
        <div class="meta-cell"><div class="label">P0 触发</div><div class="value">${t.p0_triggered?'✅':'❌'}</div></div>
        <div class="meta-cell"><div class="label">Spans</div><div class="value">${tree.total_spans}</div></div>
        <div class="meta-cell"><div class="label">Bad Case</div><div class="value">${t.is_bad_case?'⚠️ '+t.bad_case_reason:'✅ 正常'}</div></div>
      </div>
      <button class="crime-scene-btn" onclick="replayScene('${t.trace_id}')">🔍 一键还原案发现场 (Markdown)</button>
    </div>
  `;

  // 时间线
  html += `<div class="timeline"><h3>⏱️ 调用时间线 (${tree.total_spans} spans)</h3>`;
  function renderSpan(span, depth) {
    const barWidth = (span.elapsed_ms / maxMs * 100).toFixed(1);
    const barColor = span.status === 'error' ? '#cf222e' :
                     span.layer === 'L0' ? '#cf222e' :
                     span.layer === 'L1' ? '#0969da' :
                     span.layer === 'L2' ? '#8250df' :
                     span.layer === 'L3' ? '#1a7f37' :
                     span.layer === 'RAG' ? '#9a6700' : '#6e7781';
    let s = `
      <div class="span-row ${span.status === 'error' ? 'error' : ''}" onclick="toggleSpan('${span.span_id}')">
        <div class="span-toggle" style="margin-left:${depth*16}px">${span.children.length ? '▼' : '·'}</div>
        <div class="span-bar" style="width:60px;background:${barColor};height:8px"></div>
        <div class="span-name">
          ${span.name}
          ${span.layer ? `<span class="span-layer ${span.layer}">${span.layer}</span>` : ''}
        </div>
        <div class="span-elapsed">${(span.elapsed_ms||0).toFixed(1)}ms</div>
        <div class="span-status">${span.status === 'error' ? '❌' : '✅'}</div>
      </div>
    `;
    if (span.attributes && Object.keys(span.attributes).length > 0) {
      s += `<div class="span-detail" id="detail-${span.span_id}" style="display:none;margin-left:${(depth+1)*16+50}px">
        <h4>ATTRIBUTES</h4>${escapeHtml(JSON.stringify(span.attributes, null, 2))}
        ${span.error ? `<h4 style="color:#cf222e">ERROR</h4>${escapeHtml(span.error)}` : ''}
      </div>`;
    }
    if (span.children.length) {
      s += `<div class="span-children">${span.children.map(c => renderSpan(c, depth+1)).join('')}</div>`;
    }
    return s;
  }
  html += tree.root_spans.map(s => renderSpan(s, 0)).join('');
  html += `</div>`;

  // LLM 调用
  if (d.llm_calls.length) {
    html += `<div class="section"><h3>🧠 LLM 完整调用 (${d.llm_calls.length})</h3>`;
    d.llm_calls.forEach((c, i) => {
      html += `
        <div class="llm-call">
          <h4>Call ${i+1}: ${c.model} <span style="color:#586069">${c.elapsed_ms}ms</span></h4>
          <h4 style="margin-top:8px">System Prompt</h4>
          <div class="llm-prompt">${escapeHtml(c.system_prompt||'')}</div>
          <h4>User Prompt</h4>
          <div class="llm-prompt">${escapeHtml(c.user_prompt||'')}</div>
          <h4>Response</h4>
          <div class="llm-response">${escapeHtml(c.response||'')}</div>
        </div>
      `;
    });
    html += `</div>`;
  }

  // RAG 检索
  if (d.rag_hits.length) {
    html += `<div class="section"><h3>📚 RAG 检索命中 (${d.rag_hits.length})</h3>`;
    d.rag_hits.forEach(h => {
      html += `
        <div class="rag-hit">
          <div><span class="doc-id">${h.doc_id||h.name||'?'}</span>
            ${h.score ? ` · score=${h.score}` : ''}
            ${h.title ? ` · ${h.title}` : ''}
          </div>
          ${h.content_preview ? `<div style="margin-top:4px;color:#586069">${escapeHtml(h.content_preview)}</div>` : ''}
        </div>
      `;
    });
    html += `</div>`;
  }

  // Events
  if (d.events.length) {
    html += `<div class="section"><h3>📌 Events (${d.events.length})</h3>`;
    d.events.forEach(e => {
      html += `<div class="event-item"><span class="event-name">${e.name}</span>${e.payload && Object.keys(e.payload).length ? ' · ' + escapeHtml(JSON.stringify(e.payload).substring(0,200)) : ''}</div>`;
    });
    html += `</div>`;
  }

  // 错误
  if (d.errors.length) {
    html += `<div class="section" style="border-color:#cf222e"><h3 style="color:#cf222e">❌ 错误 (${d.errors.length})</h3>`;
    d.errors.forEach(e => {
      html += `<div class="event-item"><span class="event-name">${e.span_name}</span>: ${escapeHtml(e.error||'')}</div>`;
    });
    html += `</div>`;
  }

  document.getElementById('right-panel').innerHTML = html;
}

function collectSpans(span) {
  return [span, ...(span.children||[]).flatMap(collectSpans)];
}

function toggleSpan(spanId) {
  const el = document.getElementById('detail-' + spanId);
  if (el) el.style.display = el.style.display === 'none' ? 'block' : 'none';
}

async function replayScene(traceId) {
  const r = await fetch(`/api/replay/${traceId}?format=md`);
  const md = await r.text();
  const modal = document.getElementById('modal-bg');
  document.getElementById('modal-content').innerHTML = `
    <h3>🔍 案发现场还原报告</h3>
    <pre style="white-space:pre-wrap;font-size:12px;background:#f6f8fa;padding:12px;border-radius:4px;max-height:60vh;overflow:auto">${escapeHtml(md)}</pre>
    <button onclick="closeModal()" style="margin-top:12px;padding:6px 12px">关闭</button>
  `;
  modal.style.display = 'flex';
}

function closeModal() {
  document.getElementById('modal-bg').style.display = 'none';
}

function escapeHtml(s) {
  if (s == null) return '';
  return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

// Filter
document.querySelectorAll('.filter-btn').forEach(b => {
  b.addEventListener('click', () => {
    document.querySelectorAll('.filter-btn').forEach(x => x.classList.remove('active'));
    b.classList.add('active');
    state.filter = b.dataset.filter;
    loadTraces();
  });
});

// Init
loadStats();
loadTraces();
</script>
</body>
</html>"""


# ============================================================
# HTTP Handler
# ============================================================

class TraceViewerHandler(BaseHTTPRequestHandler):
    """Trace Viewer HTTP Handler"""

    def log_message(self, format, *args):
        pass  # 静默日志

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def _send_text(self, text, content_type="text/plain; charset=utf-8", status=200):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(text.encode("utf-8"))

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        if path == "/" or path == "/index.html":
            self._send_text(INDEX_HTML, "text/html; charset=utf-8")
            return

        if path == "/api/stats":
            q = TraceQuery()
            layer_stats = q.layer_stats()
            total = q.count_traces()
            p0 = q.p0_recall()
            bad = q.count_traces(is_bad_case=True)
            self._send_json({
                "total_traces": total,
                "layer_stats": layer_stats,
                "p0_recall": p0,
                "bad_cases_count": bad,
            })
            return

        if path == "/api/traces":
            q = TraceQuery()
            limit = int(qs.get("limit", ["100"])[0])
            offset = int(qs.get("offset", ["0"])[0])
            kwargs = {}
            if "final_action" in qs:
                kwargs["final_action"] = qs["final_action"][0]
            if "priority" in qs:
                kwargs["priority"] = qs["priority"][0]
            if "p0_triggered" in qs:
                kwargs["p0_triggered"] = qs["p0_triggered"][0] == "true"
            if "is_bad_case" in qs:
                kwargs["is_bad_case"] = qs["is_bad_case"][0] == "true"
            if "has_error" in qs:
                kwargs["has_error"] = qs["has_error"][0] == "true"
            traces = q.list_traces(limit=limit, offset=offset, **kwargs)
            self._send_json(traces)
            return

        if path.startswith("/api/traces/"):
            trace_id = path.split("/")[-1]
            q = TraceQuery()
            trace = q.get_trace(trace_id)
            if not trace:
                self._send_json({"error": "not found"}, status=404)
                return
            span_tree = q.get_span_tree(trace_id)
            events = q.get_events(trace_id)
            # 构造完整 detail
            llm_calls = []
            rag_hits = []
            errors = []
            for span in q.get_spans(trace_id):
                attrs = span.get("attributes", {})
                if span.get("layer") == "L3" or "prompt" in attrs or "response" in attrs:
                    llm_calls.append({
                        "span_id": span["span_id"],
                        "span_name": span["name"],
                        "model": attrs.get("model", "?"),
                        "elapsed_ms": span.get("elapsed_ms", 0),
                        "system_prompt": attrs.get("system_prompt", ""),
                        "user_prompt": attrs.get("user_prompt", attrs.get("prompt", "")),
                        "response": attrs.get("response", attrs.get("return_preview", "")),
                    })
                if span["status"] == "error" or span.get("error"):
                    errors.append({
                        "span_name": span["name"],
                        "error": span.get("error", "unknown"),
                    })
            for e in events:
                if e["name"] in ("rag_hit", "kb_hit", "retrieval"):
                    rag_hits.append(e["payload"])
            self._send_json({
                "trace": trace,
                "span_tree": span_tree,
                "events": events,
                "llm_calls": llm_calls,
                "rag_hits": rag_hits,
                "errors": errors,
            })
            return

        if path.startswith("/api/replay/"):
            trace_id = path.split("/")[-1]
            fmt = qs.get("format", ["json"])[0]
            try:
                replayer = BadCaseReplayer()
                report = replayer.replay(trace_id)
                if fmt == "md":
                    self._send_text(report.to_markdown(), "text/markdown; charset=utf-8")
                else:
                    self._send_json(report.to_dict())
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
            return

        # 404
        self._send_json({"error": "not found"}, status=404)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--host", default="127.0.0.1")
    args = p.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), TraceViewerHandler)
    print(f"🔍 Trace Viewer 已启动: http://{args.host}:{args.port}")
    print(f"   SQLite: {_ROOT / 'data' / 'observability.db'}")
    print(f"   Ctrl+C 退出")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")


if __name__ == "__main__":
    main()