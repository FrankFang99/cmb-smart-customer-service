"""
v3.12.2 本地 API Server
========================
加载真实 IntentRecognizer (含 L0 + v3.5.1/v3.6.4/v3.10.1/v3.12.1 patches)
为 GitHub Page Live Demo 提供后端识别能力

API:
  POST /api/recognize  { query: str } → IntentResult JSON
  GET  /api/scenarios  → scenarios_v3121.json 内容
  GET  /api/health     → { status: ok }
  GET  /               → 静态托管 docs/xiaozhao/

启动: python scripts/api_server_v3122.py
端口: 8889 (跟 GitHub Page 同端口, 避免冲突)
"""
import json
import sys
import time
import os
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
    """手动加 CORS 头 (避免装 flask-cors 依赖)"""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response


@app.route('/<path:_>', methods=['OPTIONS'])
def options(_):
    return '', 204

# ===== 1. 加载 IntentRecognizer (启动时一次性) =====
print('[v3.12.2 API] Loading IntentRecognizer ...')
from intent_recognizer import IntentRecognizer, IntentType
recognizer = IntentRecognizer()
print('[v3.12.2 API] IntentRecognizer loaded.')

# ===== 2. 加载 scenarios_v3121.json =====
SCENARIOS_PATH = ROOT / 'docs' / 'xiaozhao' / 'scenarios_v3121.json'
SCENARIOS = json.load(open(SCENARIOS_PATH, encoding='utf-8'))
print(f'[v3.12.2 API] Loaded {len(SCENARIOS)} scenarios.')

# ===== 3. 路由判定 =====
def get_route_label(intent_str: str, is_p0: bool, reasoning: str) -> tuple:
    """根据 reasoning 判断走的路径 (L0/L1/L2/L3)"""
    if 'v3.12.1 对抗性 L0' in reasoning or 'AML' in reasoning or '越权' in reasoning or 'FRAUD' in reasoning:
        return ('L0_HUMAN', 'L0 红线 · 100% 转人工')
    if is_p0:
        return ('L0_HUMAN', 'L0 红线 · P0 业务 · 100% 转人工')
    if reasoning.startswith('规则匹配') or reasoning.startswith('L1') or reasoning.startswith('规则命中'):
        return ('L1_RULE', 'L1 规则命中 · 不调 LLM')
    if reasoning.startswith('BERT') or reasoning.startswith('L2') or 'BERT' in reasoning:
        return ('L2_BERT', 'L2 BERT 语义相似度命中')
    if reasoning.startswith('LLM') or reasoning.startswith('L3') or 'LLM' in reasoning:
        return ('L3_LLM', 'L3 LLM 兜底 (生产调 M2.7)')
    # fallback
    return ('L3_FALLBACK', 'L3 LLM 兜底')


@app.route('/api/health')
def health():
    return jsonify({
        'status': 'ok',
        'version': 'v3.12.2',
        'recognizer_loaded': True,
        'scenarios_count': len(SCENARIOS),
    })


@app.route('/api/recognize', methods=['POST'])
def api_recognize():
    start = time.time()
    data = request.get_json(silent=True) or {}
    query = (data.get('query') or '').strip()

    if not query:
        return jsonify({'error': 'query 不能为空'}), 400

    try:
        result = recognizer.recognize(query)
        intent_str = result.intent.value if hasattr(result.intent, 'value') else str(result.intent)
        is_p0 = bool(result.is_p0)
        routing, route_label = get_route_label(intent_str, is_p0, result.reasoning)
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
    """批量评测接口 (用于本地验证 1500 条 D v3.2 真实覆盖率)"""
    data = request.get_json(silent=True) or {}
    samples = data.get('samples', [])
    if not samples:
        return jsonify({'error': 'samples 不能为空'}), 400

    results = []
    start = time.time()
    for s in samples:
        query = s.get('query', '')
        expected_intent = s.get('intent_top1', '')
        try:
            res = recognizer.recognize(query)
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
            results.append({
                'id': s.get('id'),
                'query': query,
                'error': str(e),
                'match': False,
            })

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
    print(f'[v3.12.2 API] Demo: http://localhost:{PORT}/')
    print(f'[v3.12.2 API] API:  http://localhost:{PORT}/api/recognize')
    app.run(host='127.0.0.1', port=PORT, debug=False)