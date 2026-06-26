/**
 * v3.12.1 小招 Live Demo App
 * ===========================
 * 前端交互: 12 预设场景 + 自由输入 + routing 可视化
 */

// ============================================================
// 加载 12 业务场景 (从 JSON)
// ============================================================
let SCENARIOS = [];

async function loadScenarios() {
  try {
    const res = await fetch('scenarios_v3121.json');
    SCENARIOS = await res.json();
    console.log('v3.12.1 已加载 ' + SCENARIOS.total_scenarios + ' 个业务场景');
  } catch (e) {
    console.error('加载场景失败,使用 fallback', e);
    SCENARIOS = { scenarios: [] };
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
    const latency = routing.elapsed_ms || '';
    meta.textContent = `${label} · intent=${intent} · ${latency}ms`;
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
  setText('routing-priority', pri);
  const $priBadge = document.getElementById('routing-priority');
  $priBadge.className = 'step-value priority-badge ' + pri;

  setText('routing-path', routing.route_label || routing.routing || '—');
  setText('routing-intent', routing.intent || '—');
  setText('routing-confidence', routing.confidence !== undefined ? routing.confidence : '—');
  setText('routing-action', routing.action || '—');
  setText('routing-latency', routing.elapsed_ms ? routing.elapsed_ms + 'ms' : '—');
  setText('routing-reasoning-text', routing.reasoning || '—');
}

// ============================================================
// 发送消息处理
// ============================================================
function handleUserQuery(query) {
  addMessage('user', query, null);
  showTyping();

  setTimeout(() => {
    hideTyping();
    const result = xiaozhaoAI.recognize(query);
    const answer = xiaozhaoAI.genAnswer(result.intent, query);

    const routing = {
      routing: result.routing,
      route_label: result.route_label,
      intent: result.intent,
      confidence: result.confidence,
      action: result.action,
      reasoning: result.reasoning,
      priority: result.priority,
      elapsed_ms: result.elapsed_ms,
    };

    addMessage('bot', answer, routing);
    updateRouting(routing);
  }, 250);
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
loadScenarios().then(() => {
  console.log('小招 AI v3.12.1 已就绪');
});