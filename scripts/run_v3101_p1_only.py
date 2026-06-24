"""v3.10.1 P1 子集验证 - 跑 P1 332 条, 看准确率是否回到 ≥75%"""
import sys, json, time, os, hashlib
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

# 切换到独立的 db, 不污染 v3.10.0 全量数据
from src.observability.trace_recorder import TraceRecorder
import src.observability.trace_recorder as _tr_mod
_tr_mod._recorder_singleton = TraceRecorder(db_path=_ROOT / "data" / "observability_v3101.db")

from src.agent.cascade_observable_v39 import ObservableCascadeV39

print("=" * 70)
print("v3.10.1 — P1 子集 332 条回归 (独立 DB, 不污染 v3.10.0 全量)")
print("=" * 70)

# 加载 P1 子集
eval_path = _ROOT / "data" / "D_eval_set_v3.2_dedup.json"
with open(eval_path, "r", encoding="utf-8") as f:
    eval_data = json.load(f)
eval_items = eval_data.get("samples", []) if isinstance(eval_data, dict) else eval_data
p1 = [s for s in eval_items if s.get("priority") == "P1"]
print(f"\nP1 子集: {len(p1)} 条")

os.environ.setdefault("MINIMAX_MODEL", "MiniMax-M2.7")
cascade = ObservableCascadeV39(enable_llm=True, confidence_threshold=0.85)

def _stable_trace_seed(query: str) -> str:
    return "tr_v3101_" + hashlib.md5(query.encode("utf-8")).hexdigest()[:12]

t0 = time.time()
processed = 0
correct = 0
wrong_samples = []

for i, item in enumerate(p1):
    query = item.get("query") or item.get("text") or str(item)
    expected = item.get("expected_action") or item.get("label") or "unknown"
    intent_top1 = item.get("intent_top1", "?")
    seed = _stable_trace_seed(query)

    try:
        result = cascade.handle(
            user_input=query,
            session_id=seed,
            priority="P1",
            expected_action=expected,
            intent_top1=intent_top1,
        )
        final_action = result.get("final_action", "unknown")
        p0_trig = result.get("p0_triggered", False)
        if final_action == expected:
            correct += 1
        else:
            if len(wrong_samples) < 50:
                wrong_samples.append({
                    "q": query,
                    "expected": expected,
                    "got": final_action,
                    "p0": p0_trig,
                    "intent": result.get("final_intent", "?"),
                })
    except Exception as e:
        final_action = f"ERROR: {e}"

    processed += 1
    if (i + 1) % 50 == 0:
        elapsed = time.time() - t0
        rate = (i + 1) / elapsed
        eta = (len(p1) - i - 1) / rate if rate > 0 else 0
        print(f"  [{i+1}/{len(p1)}] 累计 {elapsed:.0f}s, 预计剩余 {eta:.0f}s")

elapsed = time.time() - t0
acc = correct / len(p1) * 100
print()
print("=" * 70)
print(f"P1 准确率: {correct}/{len(p1)} = {acc:.2f}%")
print(f"耗时: {elapsed:.0f}s")
print("=" * 70)

# 输出 P1 错误样本分类 (与 v3.10.0 对比)
from collections import Counter
err_pairs = Counter()
for s in wrong_samples:
    err_pairs[(s["got"], s["expected"], s["p0"])] += 1
print("\nP1 错误样本 (前 50 条) - 按 (实际, 期望, p0) 归类:")
for (got, exp, p0), n in err_pairs.most_common():
    print(f"  final={got:25s} exp={exp:35s} p0={p0} n={n}")
print(f"\n总 P1 错误: {len(p1) - correct}")
