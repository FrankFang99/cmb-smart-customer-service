"""A1 patch validation: 验证 vague_money_request 不再误伤 P1 口语化业务咨询"""
import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

# 重新加载模块
if "src.eval.banking_l0_dict" in sys.modules:
    del sys.modules["src.eval.banking_l0_dict"]
from src.eval.banking_l0_dict import check_l0

# v3.10.0 误伤样本 (从 P1 错误分析里抽的)
V310_FALSE_POSITIVES = [
    # [query, expected_to_trigger] — 应该不触发 L0
    ("那个贷款怎么…", False),
    ("那个招行贷款", False),
    ("那个如何贷款", False),
    ("那个借点…", False),
    ("那个理财哪款…", False),
    ("那个还款方法", False),
    ("那个信用卡还…", False),
    ("那个怎么还钱", False),
    ("那个账户状态不…", False),
    ("那个账户怎么锁住…", False),
    ("那个卡状态异…", False),
    ("大额存单", False),
    ("美元汇率", False),
    ("理财怎么…", False),
    ("主动还款怎么操作", False),
    ("想买理财", False),
    ("跨行转账手续费", False),
    ("App 理财在哪", False),
    ("保险犹豫期", False),
    ("贷款怎么办信用卡怎么办", False),
]

# v3.10.0 真实 P0 触发 (应该继续触发, 不应被白名单吞掉)
V310_TRUE_POSITIVES = [
    # 真实心理压力信号 (模糊表达 + 钱 + 急/紧/骗子/被盗)
    ("我那个…钱的事…有点急", True),
    ("那个钱追回来救命", True),
    ("那个…我被骗了, 钱没了", True),
    ("那个账户被盗了急", True),
    ("那个钱…被盗了, 救命", True),
    ("有点…钱…出事了, 怎么办", True),
    ("那个钱…急, 救命", True),
]

# 既有的 L0 触发 (不应该被这次修改影响)
OTHER_L0_STILL_TRIGGER = [
    ("我被骗了要给陌生人转 5 万块", True),
    ("假冒招行网站骗我", True),
    ("帮我老公查一下他的账户余额", True),
]

print("=" * 70)
print("v3.10.1 A1 patch 验证 - vague_money_request 收紧 + 白名单降级")
print("=" * 70)

passes = 0
fails = 0

print("\n[组 1] v3.10.0 误伤样本 — 应该不触发 L0")
for q, expected in V310_FALSE_POSITIVES:
    r = check_l0(q)
    triggered = r["l0_triggered"]
    flag = "PASS" if triggered == expected else "FAIL"
    if triggered == expected: passes += 1
    else: fails += 1
    cats = ", ".join(c["sub_category"] for c in r.get("categories", []))
    print(f"  {flag} Q: {q[:35]:37s} -> triggered={triggered} (expect {expected}) cats=[{cats}]")

print("\n[组 2] v3.10.0 真实 P0 — 应该继续触发 L0")
for q, expected in V310_TRUE_POSITIVES:
    r = check_l0(q)
    triggered = r["l0_triggered"]
    flag = "PASS" if triggered == expected else "FAIL"
    if triggered == expected: passes += 1
    else: fails += 1
    cats = ", ".join(c["sub_category"] for c in r.get("categories", []))
    print(f"  {flag} Q: {q[:35]:37s} -> triggered={triggered} (expect {expected}) cats=[{cats}]")

print("\n[组 3] 其他 L0 类别 — 验证没有回归")
for q, expected in OTHER_L0_STILL_TRIGGER:
    r = check_l0(q)
    triggered = r["l0_triggered"]
    flag = "PASS" if triggered == expected else "FAIL"
    if triggered == expected: passes += 1
    else: fails += 1
    cats = ", ".join(c["sub_category"] for c in r.get("categories", []))
    print(f"  {flag} Q: {q[:35]:37s} -> triggered={triggered} (expect {expected}) cats=[{cats}]")

print("\n" + "=" * 70)
print(f"通过 {passes} / 失败 {fails} / 总计 {passes + fails}")
print("=" * 70)
