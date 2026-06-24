# -*- coding: utf-8 -*-
"""v3.10.1 P0 专项回归 — 只跑 P0 (431 条), 验证 P0 = 100% 不破.

比全量快 3x (40min → 13min), 因为 P0 路径上 L3 用本地模板, 不调 LLM.
"""
import sys, json, time, os, hashlib, shutil
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
_ROOT = Path(r'D:\Learning\AI\面试\AI智能客服')
sys.path.insert(0, str(_ROOT))

# 备份原 v3.10.1 db (保留之前 run 的结果)
prev_db = _ROOT / 'data' / 'observability_v3101_full.db'
if prev_db.exists():
    bak = _ROOT / 'data' / 'observability_v3101_full_v3p0regress.bak.db'
    if not bak.exists():
        shutil.copy(prev_db, bak)
        print(f'✓ 备份 v3.10.1 旧 db -> {bak.name}')

# 用独立 db 跑 v3.10.1 P0 回归
from src.observability.trace_recorder import TraceRecorder
import src.observability.trace_recorder as _tr_mod
new_db = _ROOT / 'data' / 'observability_v3101_p0_regress.db'
_tr_mod._recorder_singleton = TraceRecorder(db_path=new_db)
print(f'✓ v3.10.1 P0 回归 db: {new_db.name}')

from src.agent.cascade_observable_v39 import ObservableCascadeV39

print('=' * 70)
print('v3.10.1 P0 专项回归 — 431 条 P0 (验证 P0=100% 不破)')
print('=' * 70)

eval_path = _ROOT / 'data' / 'D_eval_set_v3.2_dedup.json'
with open(eval_path, 'r', encoding='utf-8') as f:
    eval_data = json.load(f)
eval_items = eval_data.get('samples', []) if isinstance(eval_data, dict) else eval_data
p0_samples = [s for s in eval_items if s.get('priority') == 'P0']
print(f'\n样本: P0 = {len(p0_samples)} 条')

os.environ.setdefault('MINIMAX_MODEL', 'MiniMax-M2.7')
cascade = ObservableCascadeV39(enable_llm=True, confidence_threshold=0.85)

def _stable_trace_seed(query, pri):
    return f"tr_v3101_p0reg_{pri}_" + hashlib.md5(query.encode('utf-8')).hexdigest()[:12]

t0 = time.time()
processed = 0
errors = []

for i, item in enumerate(p0_samples):
    query = item.get('query') or item.get('text') or str(item)
    expected = item.get('expected_action') or item.get('label') or 'unknown'
    pri = item.get('priority', '?')
    intent_top1 = item.get('intent_top1', '?')
    seed = _stable_trace_seed(query, pri)

    try:
        cascade.handle(
            user_input=query,
            session_id=seed,
            priority=pri,
            expected_action=expected,
            intent_top1=intent_top1,
        )
    except Exception as e:
        errors.append((query, str(e)[:200]))

    processed += 1
    if (i + 1) % 50 == 0:
        elapsed = time.time() - t0
        rate = (i + 1) / elapsed
        eta = (len(p0_samples) - i - 1) / rate if rate > 0 else 0
        print(f'  [{i+1}/{len(p0_samples)}] 累计 {elapsed:.0f}s, 预计剩余 {eta:.0f}s')

elapsed = time.time() - t0

# 统计
import sqlite3
c = sqlite3.connect(new_db)
cur = c.cursor()
correct = cur.execute("SELECT COUNT(*) FROM traces WHERE priority='P0' AND final_action='transfer_human'").fetchone()[0]
total = cur.execute("SELECT COUNT(*) FROM traces WHERE priority='P0'").fetchone()[0]
p0_triggered = cur.execute("SELECT COUNT(*) FROM traces WHERE priority='P0' AND p0_triggered=1").fetchone()[0]
p0_missed = cur.execute("SELECT COUNT(*) FROM traces WHERE priority='P0' AND p0_triggered=0").fetchone()[0]

# 找漏召回的 query
print()
print('=' * 70)
print(f'v3.10.1 P0 回归结果 (耗时 {elapsed:.0f}s):')
print('=' * 70)
print(f'  P0 transfer_human: {correct}/{total} = {correct/total*100:.2f}%')
print(f'  P0 triggered: {p0_triggered}/{total} = {p0_triggered/total*100:.2f}%')
print(f'  P0 missed: {p0_missed} 条')
print(f'  Errors: {len(errors)} 条')

# 找出错的
print('\n--- P0 漏召回 query (前 20 条) ---')
missed_qs = cur.execute("""SELECT user_input, expected_action, final_action, final_intent
                          FROM traces WHERE priority='P0' AND final_action!='transfer_human'
                          LIMIT 20""").fetchall()
for q, exp, fa, fi in missed_qs:
    print(f'  Q: {q[:60]}')
    print(f'    expected: {exp} | final: {fa} | intent: {fi}')

c.close()