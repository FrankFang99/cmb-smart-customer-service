"""Debug regex patterns"""
import re

text = "你好"
text_lower = text.lower()

# Test patterns
patterns = [
    r"^(你好|您好|hi|hello|hi~|hey)",
    r"^(嗯|哦|啊|呃|咦|哈)$",
    r"^$",
]

print(f"Text: '{text}'")
print(f"Text lower: '{text_lower}'")
print()

for pattern in patterns:
    result = re.search(pattern, text_lower)
    print(f"Pattern: {pattern}")
    print(f"  Match: {result}")
    print()