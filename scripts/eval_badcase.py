"""
v3.4.0 Badcase 入池脚本

把 eval_results_v340.json 的 102 个失败样本入 BadcasePool
自动定级 + 自动初判根因, PM 可后续在 BadcasePool 上 label_badcase()
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.eval.badcase_pool import BadcasePool


def main():
    eval_path = PROJECT_ROOT / "data" / "eval_results_v340.json"
    pool = BadcasePool()
    print(f"Pool: {pool.pool_path}")
    print(f"Before: {len(pool.records)} records")
    added = pool.add_from_eval_results(str(eval_path), only_failures=True)
    print(f"Imported {added} new badcases from {eval_path}")
    print(f"After: {len(pool.records)} records")
    summary = pool.weekly_summary()
    print("\n=== Weekly Summary ===")
    for k, v in summary.items():
        if k in ("p0_open_samples", "p1_open_samples"):
            print(f"  {k}: {len(v)} items")
        else:
            print(f"  {k}: {v}")
    # 导出 markdown 周报
    out = PROJECT_ROOT / "data" / "badcase" / "weekly_report.md"
    pool.export_markdown(str(out))
    print(f"\nExported weekly report: {out}")


if __name__ == "__main__":
    main()
