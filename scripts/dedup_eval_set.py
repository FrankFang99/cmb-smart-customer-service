"""
评测集去重脚本 — v3.10.0
======================

按用户要求: "不要有重复的样本" (避免评测集内部污染 + patch 过拟合)

策略:
1. 按 query 文本 hash 去重 (case-sensitive, 因为中文标点可能影响含义)
2. 保留每组的 priority / intent_top1 / expected_action (以首次出现为准)
3. 输出: data/D_eval_set_v3.2_dedup.json (独立文件, 不动原始数据)
4. 报告: 去重前后对比 + 删除样本清单

注意:
- 不动原始 D_eval_set_v3.2.json (用于可复现)
- 下游评测脚本 (run_observability_full.py 等) 改读去重版
"""
import sys
import json
import hashlib
from pathlib import Path
from collections import Counter

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))


def _query_hash(q: str) -> str:
    """query 文本稳定 hash (case-sensitive 中文标点不规范化)"""
    return hashlib.md5(q.encode("utf-8")).hexdigest()[:16]


def main():
    src_path = _ROOT / "data" / "D_eval_set_v3.2.json"
    dst_path = _ROOT / "data" / "D_eval_set_v3.2_dedup.json"

    with open(src_path, "r", encoding="utf-8") as f:
        eval_data = json.load(f)
    eval_items = eval_data.get("samples", []) if isinstance(eval_data, dict) else eval_data

    print(f"原始评测集: {len(eval_items)} 条")

    # 去重: 按 query hash
    seen = {}
    duplicates = []
    deduped = []
    for item in eval_items:
        if not isinstance(item, dict):
            # 非 dict (纯字符串) 也去重
            q = str(item)
            h = _query_hash(q)
            if h in seen:
                duplicates.append({"query": q, "reason": "string_duplicate"})
                continue
            seen[h] = {"query": q, "priority": "?"}
            deduped.append(item)
            continue

        q = item.get("query") or item.get("text") or str(item)
        h = _query_hash(q)
        if h in seen:
            duplicates.append({
                "query": q,
                "reason": "duplicate_query",
                "first_seen_priority": seen[h].get("priority"),
                "this_priority": item.get("priority", "?"),
            })
            continue
        seen[h] = {
            "query": q,
            "priority": item.get("priority", "?"),
            "intent_top1": item.get("intent_top1", "?"),
        }
        deduped.append(item)

    print(f"去重后: {len(deduped)} 条")
    print(f"删除重复: {len(duplicates)} 条")

    # 按 priority 统计
    before_pri = Counter(
        s.get("priority", "?") for s in eval_items if isinstance(s, dict)
    )
    after_pri = Counter(
        s.get("priority", "?") for s in deduped if isinstance(s, dict)
    )
    print(f"\n按 priority 对比:")
    all_pri = set(before_pri.keys()) | set(after_pri.keys())
    for pri in sorted(all_pri):
        b, a = before_pri.get(pri, 0), after_pri.get(pri, 0)
        diff = b - a
        marker = f" (-{diff})" if diff > 0 else ""
        print(f"  {pri}: {b} -> {a}{marker}")

    # 写入去重版
    out_data = eval_data.copy() if isinstance(eval_data, dict) else {}
    if isinstance(out_data, dict):
        out_data["samples"] = deduped
        out_data["dedup_info"] = {
            "original_size": len(eval_items),
            "dedup_size": len(deduped),
            "removed": len(duplicates),
            "method": "query_text_md5_hash",
            "note": "v3.10.0 patch 迭代专用, 避免重复样本污染评测 + 防止 patch 过拟合",
        }
    else:
        out_data = deduped

    dst_path.write_text(
        json.dumps(out_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n去重版已保存: {dst_path}")

    # 删除样本清单
    dup_path = _ROOT / "data" / "dedup_removed.json"
    dup_path.write_text(
        json.dumps({
            "removed_count": len(duplicates),
            "removed_samples": duplicates[:50],  # 最多展示前 50
            "note": "全部删除样本见 src/dedup_removed_full.jsonl (TODO)"
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"删除清单: {dup_path}")


if __name__ == "__main__":
    main()