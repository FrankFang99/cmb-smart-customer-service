"""Trace through all rule groups"""
import re
from src.components.intent_recognizer import IntentRecognizer
from src.config import settings

recognizer = IntentRecognizer(settings)

text = "有什么好理财"
text_lower = text.lower()

print(f"Testing: '{text}'")
print(f"Text lower: '{text_lower}'")
print()

found = False
for group_name, rules in recognizer._rule_groups:
    for pattern, intent_str in rules:
        match = re.search(pattern, text_lower)
        if match:
            print(f"MATCH in [{group_name}]: {pattern[:50]}...")
            print(f"  -> {intent_str} (matched: '{match.group()}')")
            found = True
            break
    if found:
        break

if not found:
    print("NO MATCH FOUND")