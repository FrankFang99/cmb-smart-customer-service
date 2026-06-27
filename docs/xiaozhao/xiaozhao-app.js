/**
 * v3.12.2 小招 Live Demo App
 * ===========================
 * 前端交互: 12 预设场景 + 自由输入 + routing 可视化
 *
 * 智能后端:
 *   1. 优先尝试本地 Python API (http://127.0.0.1:8889/api/recognize)
 *      - 真实 IntentRecognizer (L0 + L1 + 历史 patches)
 *      - 测试场景下用
 *   2. 本地 API 不可用 (网络错误/超时) → fallback 到 JS 规则引擎
 *      - GitHub Pages 部署场景, 静态前端不能调 API
 *      - 31 条 L1_RULES + INTENT_KEYWORDS 共现打分
 */

// ============================================================
// 配置
// ============================================================
const API_BASE = 'http://127.0.0.1:8889';
const API_TIMEOUT_MS = 5000;  // 5s 超时 fallback

// ============================================================
// 加载 12 业务场景 (从 JSON)
// ============================================================
let SCENARIOS = [];

async function loadScenarios() {
  try {
    const res = await fetch('scenarios_v3121.json');
    SCENARIOS = await res.json();
    console.log('v3.12.2 已加载 ' + SCENARIOS.total_scenarios + ' 个业务场景');
  } catch (e) {
    console.error('加载场景失败,使用 fallback', e);
    SCENARIOS = { scenarios: [] };
  }
}

// ============================================================
// 健康检查 (页面打开时测一次)
// ============================================================
async function checkAPIAvailable() {
  try {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 1500);
    const res = await fetch(`${API_BASE}/api/health`, { signal: ctrl.signal });
    clearTimeout(timer);
    if (res.ok) {
      const data = await res.json();
      console.log('[v3.12.2] 本地 API 可用:', data);
      return true;
    }
    return false;
  } catch (e) {
    console.log('[v3.12.2] 本地 API 不可用 (使用 JS 兜底引擎):', e.message);
    return false;
  }
}

// ============================================================
// DOM
// ============================================================
const $messages = document.getElementById('chat-messages');
const $input = document.getElementById('chat-input');
const $sendBtn = document.getElementById('send-btn');
const $presetButtons = document.querySelectorAll('.preset-btn');
const $routingEmpty = document.getElementById('routing-empty');
const $routingContent = document.getElementById('routing-content');
const $backendBadge = document.getElementById('backend-badge');

// ============================================================
// 消息渲染
// ============================================================
function addMessage(role, content, routing) {
  const div = document.createElement('div');
  div.className = 'message ' + (role === 'user' ? 'message-user' : 'message-bot');

  const content_div = document.createElement('div');
  content_div.className = 'message-content';

  const p = document.createElement('p');
  p.textContent = content;
  content_div.appendChild(p);

  if (routing) {
    const meta = document.createElement('span');
    meta.className = 'message-meta';
    const label = routing.route_label || (routing.routing || '');
    const intent = routing.intent || '';
    const latency = routing.elapsed_ms !== undefined ? routing.elapsed_ms : '';
    const backend = routing.backend || '';
    meta.textContent = `${label} · intent=${intent} · ${latency}ms · ${backend}`;
    content_div.appendChild(meta);
  }

  div.appendChild(content_div);
  $messages.appendChild(div);

  // 自动滚动到底
  $messages.scrollTop = $messages.scrollHeight;
}

// ============================================================
// Typing indicator
// ============================================================
function showTyping() {
  const div = document.createElement('div');
  div.className = 'message message-bot typing-message';
  div.id = 'typing-indicator';
  div.innerHTML = '<div class="message-content"><div class="typing"><span></span><span></span><span></span></div></div>';
  $messages.appendChild(div);
  $messages.scrollTop = $messages.scrollHeight;
}

function hideTyping() {
  const el = document.getElementById('typing-indicator');
  if (el) el.remove();
}

// ============================================================
// Routing 面板渲染
// ============================================================
function updateRouting(routing) {
  $routingEmpty.style.display = 'none';
  $routingContent.style.display = 'block';

  const setText = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  };

  const pri = routing.priority || 'P3';
  const $priBadge = document.getElementById('routing-priority');
  setText('routing-priority', pri);
  $priBadge.className = 'step-value priority-badge ' + pri;

  setText('routing-path', routing.route_label || routing.routing || '—');
  setText('routing-intent', routing.intent || '—');
  setText('routing-confidence', routing.confidence !== undefined ? routing.confidence : '—');
  setText('routing-action', routing.should_transfer ? 'transfer_human' : (routing.action || '—'));
  setText('routing-latency', routing.elapsed_ms !== undefined ? routing.elapsed_ms + 'ms' : '—');
  setText('routing-reasoning-text', routing.reasoning || '—');

  // 显示后端
  const backendEl = document.getElementById('routing-backend');
  if (backendEl) {
    backendEl.textContent = routing.backend || '—';
  }
}

// ============================================================
// API 调用 (本地 Python) + JS fallback
// ============================================================
async function callLocalAPI(query) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), API_TIMEOUT_MS);
  try {
    const res = await fetch(`${API_BASE}/api/recognize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query }),
      signal: ctrl.signal,
    });
    clearTimeout(timer);
    if (!res.ok) throw new Error('API 返回 ' + res.status);
    const data = await res.json();
    return {
      ...data,
      backend: 'Python API (本地)',
    };
  } catch (e) {
    clearTimeout(timer);
    throw e;
  }
}

function fallbackToJS(query) {
  // JS 规则兜底 (GitHub Pages 部署场景, 不能调 API)
  const r = xiaozhaoAI.recognize(query);
  const answer = xiaozhaoAI.genAnswer(r.intent, query);
  return {
    query,
    intent: r.intent,
    priority: r.priority,
    is_p0: r.is_p0,
    should_transfer: r.should_transfer,
    confidence: r.confidence,
    reasoning: r.reasoning,
    routing: r.routing,
    route_label: r.route_label,
    action: r.action,
    answer,
    elapsed_ms: parseFloat(r.elapsed_ms) || 0,
    backend: 'JS 规则引擎 (前端兜底)',
  };
}

async function recognize(query) {
  try {
    const apiResult = await callLocalAPI(query);
    // API 返回不带 answer, 本地用 JS genAnswer 生成
    apiResult.answer = xiaozhaoAI.genAnswer(apiResult.intent, query);
    return apiResult;
  } catch (e) {
    console.log('[v3.12.2] 本地 API 失败, fallback 到 JS 规则:', e.message);
    return fallbackToJS(query);
  }
}

// ============================================================
// 发送消息处理
// ============================================================
async function handleUserQuery(query) {
  addMessage('user', query, null);
  showTyping();

  try {
    const result = await recognize(query);
    hideTyping();
    const routing = {
      routing: result.routing,
      route_label: result.route_label,
      intent: result.intent,
      confidence: result.confidence,
      should_transfer: result.should_transfer,
      action: result.action,
      reasoning: result.reasoning,
      priority: result.priority,
      elapsed_ms: result.elapsed_ms,
      backend: result.backend,
    };
    addMessage('bot', result.answer, routing);
    updateRouting(routing);
  } catch (e) {
    hideTyping();
    addMessage('bot', '抱歉,识别服务暂时不可用,请稍后再试。', null);
    console.error('[v3.12.2] handleUserQuery error:', e);
  }
}

// ============================================================
// 事件绑定
// ============================================================
$sendBtn.addEventListener('click', () => {
  const query = $input.value.trim();
  if (!query) return;
  handleUserQuery(query);
  $input.value = '';
});

$input.addEventListener('keypress', (e) => {
  if (e.key === 'Enter') {
    $sendBtn.click();
  }
});

// 预设场景按钮
$presetButtons.forEach(btn => {
  btn.addEventListener('click', async () => {
    const sid = btn.getAttribute('data-scenario');
    const sc = SCENARIOS.scenarios.find(s => s.id === sid);
    if (!sc) return;

    // 清空聊天
    $messages.innerHTML = '';

    // 播放场景: 依次展示每个 user turn + assistant turn
    for (let i = 0; i < sc.turns.length; i++) {
      const turn = sc.turns[i];
      if (turn.role === 'user') {
        addMessage('user', turn.content, null);
        await sleep(150);

        // 取下一个 assistant
        const next = sc.turns[i + 1];
        if (next && next.role === 'assistant') {
          showTyping();
          await sleep(300);
          hideTyping();
          addMessage('bot', next.content, next.routing);
          updateRouting(next.routing);
          i++; // skip next
        }
        await sleep(300);
      }
    }
  });
});

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// ============================================================
// Init
// ============================================================
async function init() {
  await loadScenarios();
  const apiAvailable = await checkAPIAvailable();

  // 设置后端 badge
  if ($backendBadge) {
    if (apiAvailable) {
      $backendBadge.textContent = '🟢 本地 Python API';
      $backendBadge.className = 'backend-badge backend-online';
    } else {
      $backendBadge.textContent = '🟡 JS 兜底引擎 (无本地 API)';
      $backendBadge.className = 'backend-badge backend-offline';
    }
  }

  console.log(`小招 AI v3.12.2 已就绪, 后端: ${apiAvailable ? 'Python API (本地)' : 'JS 兜底'}`);
}

init();