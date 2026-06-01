"""Test patterns against known strings"""
import re

test_cases = [
    ("有什么好理财", "sales_wealth_prod", "推荐.*理财|理财推荐|想买理财|好.*理财|有什么好"),
    ("推荐理财产品", "sales_wealth_prod", "推荐.*理财|理财推荐|想买理财|好.*理财|有什么好"),
    ("贷款推荐", "sales_loan_prod", "贷款推荐|信用贷推荐|推荐贷款|推荐.*贷款|贷款.*推荐|贷.*推荐|有什么.*产品|好.*产品推荐"),
    ("有什么贷款产品", "sales_loan_prod", "贷款推荐|信用贷推荐|推荐贷款|推荐.*贷款|贷款.*推荐|贷.*推荐|有什么.*产品|好.*产品推荐"),
    ("推荐信用卡", "sales_credit_prod", "信用卡推荐|办卡|申请卡|推荐.*信用卡|推荐.*卡|办.*卡|申请.*卡|推荐.*信用.*卡"),
    ("最晚什么时候还款", "info_bill_date", "还款日|几号还|截止日期|哪天还款|什么时候还款|最晚.*还款|还款时间|什么时间还款"),
]

print("Testing patterns:")
for text, expected, pattern in test_cases:
    match = re.search(pattern, text.lower())
    result = match.group(0) if match else "NO MATCH"
    print(f"'{text}'")
    print(f"  Pattern: {pattern}")
    print(f"  Match: {result}")
    print(f"  Expected: {expected}")
    print()