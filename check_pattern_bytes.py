"""Check actual pattern bytes"""
import re
from src.components.intent_recognizer import IntentRecognizer
from src.config import settings

recognizer = IntentRecognizer(settings)

text = "有什么好理财"
text_lower = text.lower()

# Get first sales_wealth_prod pattern
pattern_str = recognizer._sales_rules[0][0]
print(f"Pattern: '{pattern_str}'")
print(f"Pattern bytes: {pattern_str.encode('utf-8').hex()}")
print(f"Pattern repr: {repr(pattern_str)}")
print()

# Decode the bytes to see what's there
print("Pattern bytes decoded:")
# Split into pairs and decode
bytes_list = [pattern_str[i:i+2] for i in range(0, len(pattern_str), 2)]
for b in bytes_list[:10]:
    try:
        print(f"  {b} -> {b.encode('utf-8').decode('utf-8')}")
    except:
        print(f"  {b} -> (cannot decode)")

# Check if the pattern contains lowercase '好'
print()
print(f"'好' in pattern: {'好' in pattern_str}")
print(f"'好' lowercase: {'好'.lower()}")

# Test with the actual pattern
print()
match = re.search(pattern_str, text_lower)
print(f"Match with pattern_str: {match}")
if match:
    print(f"  Matched: '{match.group()}'")