"""Debug specific patterns that still fail"""
import re

# Check what matches "有什么好理财"
text = "有什么好理财"
text_lower = text.lower()

# PRODUCT rules (higher priority)
product_patterns = [
    r"理财(产品|收益|安全|风险|怎么|多少)",
]
# SALES rules (lower priority)
sales_patterns = [
    r"推荐.*理财|理财推荐|想买理财|好.*理财|有什么好",
]

print(f"Testing: '{text}'")
print("PRODUCT rules:")
for p in product_patterns:
    match = re.search(p, text_lower)
    if match:
        print(f"  MATCH: {p} -> {match.group()}")

print("SALES rules:")
for p in sales_patterns:
    match = re.search(p, text_lower)
    if match:
        print(f"  MATCH: {p} -> {match.group()}")