"""Debug specific patterns"""
import re

test_cases = [
    ("申请信用卡", "sales_credit_prod"),
    ("贷款推荐", "sales_loan_prod"),
    ("查一下交易明细", "info_tran_record"),
]

# Product rules
product_rules = [
    (r"信用卡额度|信用卡年费|信用卡申请|信用卡产品", "cons_prod_credit"),
    (r"信用(卡|贷).*(额度|年费|申请|产品|怎么|好|哪个|推荐)", "cons_prod_credit"),
    (r"贷款(利率|条件|额度|产品)?", "cons_prod_loan"),
]

# Sales rules
sales_rules = [
    (r"信用卡推荐|办卡|申请卡|推荐.*信用卡|推荐.*卡|办.*卡|申请.*卡", "sales_credit_prod"),
    (r"贷款推荐|信用贷推荐|推荐贷款|推荐.*贷款", "sales_loan_prod"),
]

print("Testing patterns:")
for text in test_cases:
    q = text[0]
    expected = text[1]
    print(f"\n'{q}' (expected: {expected})")
    print("  PRODUCT rules:")
    for pattern, intent in product_rules:
        match = re.search(pattern, q)
        if match:
            print(f"    MATCH: {pattern} -> {intent}")
    print("  SALES rules:")
    for pattern, intent in sales_rules:
        match = re.search(pattern, q)
        if match:
            print(f"    MATCH: {pattern} -> {intent}")