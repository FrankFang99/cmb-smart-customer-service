# -*- coding: utf-8 -*-
"""v3.10.1 全量跑 (使用新 dedup eval set + 新 P0/L1 patches)
验证 P0=100% + P1 >= 75% + 完整 P2/P3
"""
import sys, json, time, os, hashlib, shutil
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
_ROOT = Path(r'D:\Learning\AI\面试\AI智能客服')
sys.path.insert(0, str(_ROOT))

# 备份原 v3.10.1 db
prev_db = _ROOT / 'data' / 'observability_v3101_full.db'
if prev_db.exists():
    bak = _ROOT / 'data' / 'observability_v3101_full_v3p0regress_v2.bak.db'
    if not bak.exists():
        shutil.copy(prev_db, bak)
        print(f'✓ 备份 v3.10.1 旧 db -> {bak.name}')

# 新 db
from src.observability.trace_recorder import TraceRecorder
import src.observability.trace_recorder as _tr_mod
new_db = _ROOT / 'data' / 'observability_v3101_v3.db'
_tr_mod._recorder_singleton = TraceRecorder(db_path=new_db)
print(f'✓ v3.10.1 v3 db: {new_db.name}')

from src.agent.cascade_observable_v39 import ObservableCascadeV39

print('=' * 70)
print('v3.10.1 v3 — 全量 1076 条 (使用新 dedup_v3101 eval set + 新 patches)')
print('=' * 70)

# 用新 dedup_v3101 eval set
eval_path = _ROOT / 'data' / 'D_eval_set_v3.2_dedup_v3101.json'
with open(eval_path, 'r', encoding='utf-8') as f:
    eval_data = json.load(f)
eval_items = eval_data.get('samples', []) if isinstance(eval_data, dict) else eval_data
p0 = [s for s in eval_items if s.get('priority') == 'P0']
p1 = [s for s in eval_items if s.get('priority') == 'P1']
p2 = [s for s in eval_items if s.get('priority') == 'P2']
p3 = [s for s in eval_items if s.get('priority') == 'P3']
samples = p0 + p1 + p2 + p3
print(f'\n样本分布: P0:{len(p0)} P1:{len(p1)} P2:{len(p2)} P3:{len(p3)} = {len(samples)} 条')

os.environ.setdefault('MINIMAX_MODEL', 'MiniMax-M2.7')
cascade = ObservableCascadeV39(enable_llm=True, confidence_threshold=0.85)

def _stable_trace_seed(query, pri):
    return f"tr_v3101v3_{pri}_" + hashlib.md5(query.encode('utf-8')).hexdigest()[:12]

t0 = time.time()
processed = 0
errors = []

for i, item in enumerate(samples):
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
    if (i + 1) % 100 == 0:
        elapsed = time.time() - t0
        rate = (i + 1) / elapsed
        eta = (len(samples) - i - 1) / rate if rate > 0 else 0
        print(f'  [{i+1}/{len(samples)}] 累计 {elapsed:.0f}s, 预计剩余 {eta:.0f}s')

elapsed = time.time() - t0

# 统计
import sqlite3
c = sqlite3.connect(new_db)
cur = c.cursor()
buckets = {"P0": [0, 0], "P1": [0, 0], "P2": [0, 0], "P3": [0, 0]}
for r in cur.execute("SELECT priority, final_action FROM traces"):
    pri, final = r[0], r[1]
    if pri not in buckets: continue
    buckets[pri][1] += 1
    if pri == "P0":
        if final == "transfer_human": buckets[pri][0] += 1
    else:
        if final in ("answer", "clarify", "fallback_to_human"): buckets[pri][0] += 1

p0_recall = {}
for pri in ["P0", "P1", "P2", "P3"]:
    cur2 = c.cursor()
    triggered = cur2.execute("SELECT COUNT(*) FROM traces WHERE priority=? AND p0_triggered=1", (pri,)).fetchone()[0]
    total = cur2.execute("SELECT COUNT(*) FROM traces WHERE priority=?", (pri,)).fetchone()[0]
    p0_recall[pri] = {"total": total, "p0_caught": triggered, "recall_rate": triggered/total if total>0 else 0}

cur2 = c.cursor()
bad_n = cur2.execute("SELECT COUNT(*) FROM traces WHERE is_bad_case=1").fetchone()[0]

print()
print('=' * 70)
print(f'v3.10.1 v3 全量结果 (耗时 {elapsed:.0f}s):')
print('=' * 70)
for pri, (correct, total) in buckets.items():
    rate = correct/total*100 if total > 0 else 0
    print(f'  {pri}: {correct}/{total} = {rate:.2f}%')
print()
print('P0 召回:')
for pri, r in p0_recall.items():
    print(f'  {pri}: {r["p0_caught"]}/{r["total"]} = {r["recall_rate"]*100:.2f}%')
print()
print(f'Bad Case (自动检测): {bad_n} 条')

# 写报告
report = {
    "version": "v3.10.1-v3-full",
    "run_date": time.strftime('%Y-%m-%dT%H:%M:%S'),
    "sample_size": len(samples),
    "processed": processed,
    "errors_count": len(errors),
    "total_elapsed_sec": round(elapsed, 1),
    "action_accuracy_full": {pri: {"correct": c, "total": t, "rate": c/t if t>0 else 0} for pri, (c, t) in buckets.items()},
    "p0_recall": p0_recall,
    "bad_cases_count": bad_n,
    "patches_applied": [
        "v364: +9 AML cross-border short queries (给国外汇钱 等)",
        "l0_v3101: cross_border_suspicious +10 短 query keywords",
        "l3_v3101: P0 模板兜底 (跳过 LLM)",
        "d_v32_dedup_v3101: 57 条 真·P0 priority 升级",
        "v364 biz_transfer_large: 收紧 (删 怎么办/怎么操作/大额 单独)",
        "l0_v3101 large_amount: 收紧 (删 大额 单独, 保留 大额转/汇)",
    ],
}
report_path = _ROOT / 'data' / 'observable_v3101_v3_report.json'
report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'\n报告: {report_path}')

# 找 P1 错答 (Top expected_action)
print('\n=== P1 transfer_human 错答 Top 10 expected_action ===')
for r in cur.execute("""
    SELECT expected_action, COUNT(*) FROM traces
    WHERE priority='P1' AND final_action='transfer_human'
    GROUP BY expected_action ORDER BY 2 DESC LIMIT 10
"""):
    print(f'  {r[0]}: {r[1]} 条')

c.close()