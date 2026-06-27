"""
v3.12.2 本地 API Server (含 Mock 业务数据库)
=============================================
加载真实 IntentRecognizer (L0 + L1 + L2 BERT + L3 LLM)
为 GitHub Page Live Demo 提供:
  - 真实意图识别
  - Mock 业务数据库 (账户/信用卡/营销/知识库) → 真实可读的答案
  - 完整 routing 可视化 (含数据源)

API:
  POST /api/recognize  { query: str } → IntentResult JSON (含 answer + data_sources)
  GET  /api/scenarios  → scenarios_v3121.json 内容
  GET  /api/health     → { status: ok }
  GET  /               → 静态托管 docs/xiaozhao/

启动: python scripts/api_server_v3122.py
端口: 8889
"""
import json
import sys
import time
from pathlib import Path

# 把项目根加进 sys.path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src' / 'components'))
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'src' / 'eval'))

from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder=None)


@app.after_request
def add_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response


@app.route('/<path:_>', methods=['OPTIONS'])
def options(_):
    return '', 204

# ===== 1. 加载 IntentRecognizer =====
print('[v3.12.2 API] Loading IntentRecognizer ...')
from intent_recognizer import IntentRecognizer
recognizer = IntentRecognizer()
print('[v3.12.2 API] IntentRecognizer loaded.')

# ===== 2. 加载 Mock 业务数据库 =====
sys.path.insert(0, str(ROOT / 'scripts'))
from mock_biz_db import gen_answer as mock_gen_answer
print('[v3.12.2 API] Mock business DB loaded.')

# ===== 3. 加载 scenarios =====
SCENARIOS_PATH = ROOT / 'docs' / 'xiaozhao' / 'scenarios_v3121.json'
SCENARIOS = json.load(open(SCENARIOS_PATH, encoding='utf-8'))
print(f'[v3.12.2 API] Loaded {len(SCENARIOS)} scenarios.')


# ===== 4. 路由判定 + 答案生成 =====
def get_route_label(intent_str: str, is_p0: bool, reasoning: str) -> tuple:
    if 'v3.12.1 对抗性 L0' in reasoning or 'AML' in reasoning or '越权' in reasoning:
        return ('L0_HUMAN', 'L0 红线 · 对抗性 · 100% 转人工')
    if is_p0:
        return ('L0_HUMAN', 'L0 红线 · P0 业务 · 100% 转人工')
    if 'L2 BERT' in reasoning:
        return ('L2_BERT', 'L2 BERT 语义相似度命中 (30 label 模型)')
    if 'L3 LLM' in reasoning:
        return ('L3_LLM', 'L3 LLM 兜底 (MiniMax M2.7, 启用 thinking 模式)')
    if '规则匹配' in reasoning:
        return ('L1_RULE', 'L1 规则命中 · 不调模型/LLM')
    return ('L3_FALLBACK', 'L3 LLM 兜底 (sys_invalid)')


@app.route('/api/health')
def health():
    return jsonify({
        'status': 'ok',
        'version': 'v3.12.2',
        'recognizer_loaded': True,
        'mock_db_loaded': True,
        'scenarios_count': len(SCENARIOS),
    })


@app.route('/api/recognize', methods=['POST'])
def api_recognize():
    start = time.time()
    data = request.get_json(silent=True) or {}
    query = (data.get('query') or '').strip()

    if not query:
        return jsonify({'error': 'query 不能为空'}), 400

    # 用 use_llm 开关控制 (默认 True, 支持 L3)
    use_llm = bool(data.get('use_llm', True))

    try:
        result = recognizer.recognize(query, use_llm=use_llm)
        intent_str = result.intent.value if hasattr(result.intent, 'value') else str(result.intent)
        is_p0 = bool(result.is_p0)
        routing, route_label = get_route_label(intent_str, is_p0, result.reasoning)

        # ===== 调 Mock DB 生成真实答案 =====
        answer, data_sources = mock_gen_answer(intent_str, query)

        # ===== sys_invalid 兜底 (mock_biz_db._keyword_fallback 已经处理关键词路由) =====
        # 如果 mock_gen_answer 还是返回了"抱歉没理解"的兜底文案, 才给"建议转人工"
        # _keyword_fallback 命中 → data_sources 会含真实数据源 (如 金融市场系统), 这里不会触发
        if '抱歉, 您的问题暂时不在我的能力范围内' in answer:
            if 'LLM' in result.reasoning:
                # L3 跑了但没给出有效标签, 走关键词兜底也失败
                answer = (
                    '我尝试了多种方式理解您的问题, 但暂时无法准确识别。\n\n'
                    '**建议直接转人工** (0 等待):\n'
                    '  - 输入 "转人工" 接入客服\n'
                    '  - 拨 95555 (7×24)\n'
                    '  - 紧急情况请拨 110\n\n'
                    '🔔 我已记录本次问题, 用于持续优化'
                )
                data_sources = ['意图识别失败 (建议转人工)']
            else:
                # L1/L2 漏了, L3 没开, 同样建议转人工
                answer = (
                    '抱歉, 我暂时无法理解您的问题, 但转人工可以更快解决。\n\n'
                    '**建议直接转人工** (0 等待):\n'
                    '  - 输入 "转人工"\n'
                    '  - 或拨 95555\n'
                )
                data_sources = ['意图识别失败 (建议转人工)']

        elapsed_ms = (time.time() - start) * 1000

        return jsonify({
            'query': query,
            'intent': intent_str,
            'priority': 'P0' if is_p0 else 'P1/P2/P3',
            'is_p0': is_p0,
            'should_transfer': bool(result.should_transfer),
            'confidence': round(float(result.confidence), 4),
            'reasoning': result.reasoning,
            'routing': routing,
            'route_label': route_label,
            'answer': answer,
            'data_sources': data_sources,  # 接入的数据源 (给 routing 面板展示)
            'slots': result.slots or {},
            'elapsed_ms': round(elapsed_ms, 2),
        })
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc(),
        }), 500


@app.route('/api/scenarios')
def api_scenarios():
    return jsonify(SCENARIOS)


@app.route('/api/batch_eval', methods=['POST'])
def api_batch_eval():
    """批量评测接口"""
    data = request.get_json(silent=True) or {}
    samples = data.get('samples', [])
    use_llm = bool(data.get('use_llm', False))
    if not samples:
        return jsonify({'error': 'samples 不能为空'}), 400

    results = []
    start = time.time()
    for s in samples:
        query = s.get('query', '')
        expected_intent = s.get('intent_top1', '')
        try:
            res = recognizer.recognize(query, use_llm=use_llm)
            intent_str = res.intent.value if hasattr(res.intent, 'value') else str(res.intent)
            results.append({
                'id': s.get('id'),
                'query': query,
                'expected': expected_intent,
                'predicted': intent_str,
                'is_p0': bool(res.is_p0),
                'reasoning': res.reasoning,
                'match': intent_str == expected_intent,
            })
        except Exception as e:
            results.append({'id': s.get('id'), 'query': query, 'error': str(e), 'match': False})

    elapsed = time.time() - start
    total = len(results)
    matched = sum(1 for r in results if r.get('match'))
    return jsonify({
        'total': total,
        'matched': matched,
        'match_rate': round(matched / total * 100, 2) if total else 0,
        'elapsed_sec': round(elapsed, 2),
        'qps': round(total / elapsed, 1) if elapsed else 0,
        'results': results,
    })


# ===== 静态托管 docs/xiaozhao/ =====
@app.route('/')
def index():
    return send_from_directory(str(ROOT / 'docs' / 'xiaozhao'), 'index.html')


@app.route('/<path:path>')
def static_files(path):
    return send_from_directory(str(ROOT / 'docs' / 'xiaozhao'), path)


if __name__ == '__main__':
    PORT = 8889
    print(f'\n[v3.12.2 API] Listening on http://localhost:{PORT}')
    print(f'[v3.12.2 API] Demo:  http://localhost:{PORT}/')
    print(f'[v3.12.2 API] API:   http://localhost:{PORT}/api/recognize')
    app.run(host='127.0.0.1', port=PORT, debug=False, threaded=True)