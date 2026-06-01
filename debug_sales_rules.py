"""Debug SALES rules by checking pattern order"""
from src.components.intent_recognizer import IntentRecognizer
from src.config import settings
import re

recognizer = IntentRecognizer(settings)

# Get the rule groups order
print("Rule groups order:")
for name, _ in recognizer._rule_groups:
    print(f"  {name}")
print()

# Check which group contains the sales_rules
for name, rules in recognizer._rule_groups:
    if rules is recognizer._sales_rules:
        print(f"SALES is at: {name}")
        break

# Check what PRODUCT rules look like
print("\nPRODUCT rules:")
for pattern, intent in recognizer._product_rules[:5]:
    print(f"  {pattern} -> {intent}")

# Test matching
print("\nMatching test:")
text = "有什么好理财"
text_lower = text.lower()
print(f"Text: {text_lower}")

# Try PRODUCT rules first
print("\nTrying PRODUCT rules:")
for pattern, intent in recognizer._product_rules:
    match = re.search(pattern, text_lower)
    if match:
        print(f"  MATCH: {pattern} -> {intent}")
        break

# Then SALES rules
print("\nTrying SALES rules:")
for pattern, intent in recognizer._sales_rules:
    match = re.search(pattern, text_lower)
    if match:
        print(f"  MATCH: {pattern} -> {intent}")
        break