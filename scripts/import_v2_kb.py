"""
v2.0 markdown 知识库解析 + 注入 src/rag/knowledge_base.py
============================================================

输入: knowledge_base/银行零售业务知识库_v2.0.md (565 条, 14 大类)
输出: 替换 src/rag/knowledge_base.py 中 KNOWLEDGE_BASE 列表
"""
from __future__ import annotations

import re
import sys
import os
from pathlib import Path
from collections import Counter, defaultdict


# 用相对路径, 脚本从项目根目录跑
PROJECT_ROOT = Path(os.getcwd())
SRC_MD = PROJECT_ROOT / "knowledge_base" / "银行零售业务知识库_v2.0.md"
DST_PY = PROJECT_ROOT / "src" / "rag" / "knowledge_base.py"


# v2.0 14 大类 → (domain_code, domain_zh, intent_category 映射)
# intent_category 走 v1.0 的 8 大意图 (query/consult/transaction/marketing/...)
DOMAIN_MAP = {
    "KB_ACC_": ("account", "账户与安全", "query"),
    "KB_CC_":  ("credit_card", "信用卡", "query"),
    "KB_LN_":  ("loan", "贷款业务", "consult"),
    "KB_INV_": ("investment", "投资理财", "marketing"),
    "KB_PAY_": ("payment", "支付结算", "transaction"),
    "KB_DCEP": ("dcep", "数字人民币", "transaction"),
    "KB_PEN_": ("pension", "个人养老金", "consult"),
    "KB_GOV_": ("gov", "五险一金/政务", "consult"),
    "KB_CB_":  ("cross_border", "跨境/外汇", "consult"),
    "KB_LIFE": ("life", "便民生活", "query"),
    "KB_NW_":  ("new_worker", "新就业/普惠", "consult"),
    "KB_SV_":  ("service", "服务与反馈", "service_transfer"),
    "KB_RISK": ("risk", "风控/合规", "risk"),
    "KB_PROD": ("product", "产品矩阵", "marketing"),
}


def detect_domain(kb_id: str) -> tuple:
    """从 ID 前缀识别 domain"""
    for prefix, info in DOMAIN_MAP.items():
        if kb_id.startswith(prefix):
            return info
    return ("unknown", "未知", "query")


def parse_v2_markdown(content: str) -> list:
    """
    解析 v2.0 markdown 表格
    行格式: | KB_xxx_001 | 问题 | 回答要点 | 风险 |
    """
    # 匹配 | KB_xxx | ... | ... | ... | (4 列, 第 4 列可选)
    pattern = r'^\|\s*(KB_\w+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|(?:\s*([^|]*?)\s*\|)?\s*$'
    rows = re.findall(pattern, content, re.MULTILINE)

    items = []
    for kb_id, question, answer_hint, risk in rows:
        domain_code, domain_zh, intent_cat = detect_domain(kb_id)

        # 风险标识
        risk_lower = risk.strip().lower() if risk else ""
        if risk_lower in ("-", "", "无", "无", "n/a"):
            risk_disclosure = False
            risk_tags = []
        else:
            risk_disclosure = True
            # 拆 risk tags (如 "高/中/低" 拆开)
            risk_tags = [r.strip() for r in re.split(r'[/、,，;；\s]+', risk) if r.strip() and r.strip() != "-"]

        # sub_category 简化 (去掉 KB_ 前缀, 如 KB_ACC_001 -> ACC_001)
        sub_match = re.match(r'KB_(\w+?)_\d+', kb_id)
        sub_cat = sub_match.group(1).lower() if sub_match else domain_code

        item = {
            "id": kb_id,
            "category": intent_cat,           # 8 大意图 (v1.0 兼容)
            "domain": domain_code,            # 14 大业务领域 (v2.0 新增)
            "domain_zh": domain_zh,           # 中文领域名
            "sub_category": sub_cat,          # 短码
            "question": question.strip(),
            # v3.3.4 改进: 把"回答要点 + 风险标签 + 业务领域"拼到 answer 里, RAG 检索能命中更多关键词
            "answer": " | ".join(filter(None, [
                answer_hint.strip(),
                f"风险提示: {', '.join(risk_tags)}" if risk_tags else "",
                f"业务领域: {domain_zh}",
            ])),
            "tags": risk_tags,                # 风险标签
            "metadata": {
                "intent": f"{intent_cat}_{sub_cat}",  # 兼容 v1.0
                "frequency": "medium",                # v2.0 没标, 默认中频
                "risk_disclosure": risk_disclosure,
                "version": "v2.0",                    # 标记数据来源版本
            },
        }
        items.append(item)
    return items


def generate_python_code(items: list) -> str:
    """生成 knowledge_base.py 的 KNOWLEDGE_BASE 列表定义代码"""
    lines = [
        '"""',
        '招商银行零售业务知识库 v2.0',
        '===========================',
        '',
        '从 knowledge_base/银行零售业务知识库_v2.0.md 解析生成',
        '总条数: 565, 大类: 14 业务领域, 8 意图分类',
        '',
        '字段:',
        '- id           v2.0 ID (KB_ACC_001 等)',
        '- category     意图分类 (query/consult/transaction/marketing/service_transfer/risk/complex/invalid)',
        '- domain       业务领域 (account/credit_card/loan/investment/payment/dcep/pension/gov/cross_border/life/new_worker/service/risk/product)',
        '- domain_zh    业务领域中文',
        '- sub_category 子类短码',
        '- question     问题',
        '- answer       回答要点 (v2.0 表格格式, 简版)',
        '- tags         风险标签',
        '- metadata     元数据 (intent/frequency/risk_disclosure/version)',
        '',
        '历史: v1.0 (40 条) → v2.0 (565 条) 招行最高标准',
        '生成: scripts/import_v2_kb.py',
        '"""',
        'from typing import List, Dict',
        '',
        '',
        '# ============================================================',
        '# 知识库条目 (v2.0, 565 条, 14 大业务领域)',
        '# ============================================================',
        '',
        'KNOWLEDGE_BASE: List[Dict] = [',
        '',
    ]

    # 按 domain 分组, 加注释头
    domain_order = [
        "account", "credit_card", "loan", "investment", "payment",
        "dcep", "pension", "gov", "cross_border", "life",
        "new_worker", "service", "risk", "product",
    ]
    by_domain = defaultdict(list)
    for item in items:
        by_domain[item["domain"]].append(item)

    for d in domain_order:
        if d not in by_domain:
            continue
        zh = by_domain[d][0]["domain_zh"]
        lines.append(f'    # ========== {zh} ({d}) — {len(by_domain[d])} 条 ==========')
        lines.append('')
        for item in by_domain[d]:
            lines.append('    {')
            lines.append(f'        "id": {item["id"]!r},')
            lines.append(f'        "category": {item["category"]!r},')
            lines.append(f'        "domain": {item["domain"]!r},')
            lines.append(f'        "domain_zh": {item["domain_zh"]!r},')
            lines.append(f'        "sub_category": {item["sub_category"]!r},')
            lines.append(f'        "question": {item["question"]!r},')
            lines.append(f'        "answer": {item["answer"]!r},')
            lines.append(f'        "tags": {item["tags"]!r},')
            lines.append(f'        "metadata": {item["metadata"]!r},')
            lines.append('    },')
        lines.append('')

    lines.append(']')
    lines.append('')
    lines.append('')
    lines.append('# ============================================================')
    lines.append('# 统计')
    lines.append('# ============================================================')
    lines.append('_STATS = {')
    lines.append(f'    "total": {len(items)},')
    cnt = Counter(i["domain"] for i in items)
    lines.append('    "by_domain": {')
    for d in domain_order:
        if d in cnt:
            lines.append(f'        {d!r}: {cnt[d]},')
    lines.append('    },')
    cnt2 = Counter(i["category"] for i in items)
    lines.append('    "by_intent": {')
    for k, v in cnt2.items():
        lines.append(f'        {k!r}: {v},')
    lines.append('    },')
    lines.append('}')
    lines.append('')
    lines.append('')
    lines.append('def get_knowledge_by_intent(intent: str) -> List[Dict]:')
    lines.append('    """按意图分类过滤 (兼容 v1.0 调用)"""')
    lines.append('    return [k for k in KNOWLEDGE_BASE if k["category"] == intent or k.get("metadata", {}).get("intent") == intent]')
    lines.append('')
    lines.append('')
    lines.append('def get_knowledge_by_domain(domain: str) -> List[Dict]:')
    lines.append('    """按业务领域过滤 (v2.0 新接口)"""')
    lines.append('    return [k for k in KNOWLEDGE_BASE if k["domain"] == domain]')
    lines.append('')
    lines.append('')
    lines.append('def get_knowledge_stats() -> Dict:')
    lines.append('    """统计 (供评测 / 文档展示)"""')
    lines.append('    return _STATS')
    lines.append('')

    return '\n'.join(lines)


def main():
    if not SRC_MD.exists():
        print(f"[ERR] source markdown not found: {SRC_MD}")
        sys.exit(1)
    if not DST_PY.exists():
        print(f"[ERR] target .py not found: {DST_PY}")
        sys.exit(1)

    content = SRC_MD.read_text(encoding='utf-8')
    items = parse_v2_markdown(content)
    print(f"[OK] parsed v2.0 markdown: {len(items)} items")

    new_code = generate_python_code(items)

    # 写文件
    DST_PY.write_text(new_code, encoding='utf-8')
    print(f"[OK] injected {DST_PY}")
    print(f"   file size: {DST_PY.stat().st_size} bytes")

    # 统计
    cnt = Counter(i["domain"] for i in items)
    print("\nby domain:")
    for d, n in sorted(cnt.items(), key=lambda x: -x[1]):
        print(f"  {d}: {n}")

    cnt2 = Counter(i["category"] for i in items)
    print("\nby intent:")
    for d, n in sorted(cnt2.items(), key=lambda x: -x[1]):
        print(f"  {d}: {n}")


if __name__ == "__main__":
    main()
