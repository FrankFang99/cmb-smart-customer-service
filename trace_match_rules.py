"""Trace through _match_rules step by step"""
import re

# Simulate what _match_rules does
sales_rules = [
    (r"推荐.*理财|理财推荐|想买理财|好.*理财|有什么好", "sales_wealth_prod"),
]

text = "有什么好理财"
text_lower = text.lower()

print(f"Text: '{text}'")
print(f"Text lower: '{text_lower}'")
print()

print("Testing each pattern:")
for i, (pattern, intent) in enumerate(sales_rules):
    print(f"Pattern {i}: {pattern}")
    print(f"  repr: {repr(pattern)}")
    match = re.search(pattern, text_lower)
    print(f"  Match: {match}")
    if match:
        print(f"  Matched text: '{match.group()}'")
    print()