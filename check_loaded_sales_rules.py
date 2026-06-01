"""Check actual loaded sales rules"""
import importlib
import sys

# Clear any cached imports
for mod_name in list(sys.modules.keys()):
    if 'intent_recognizer' in mod_name or 'src' in mod_name:
        del sys.modules[mod_name]

# Fresh import
from src.components.intent_recognizer import IntentRecognizer
from src.config import settings

recognizer = IntentRecognizer(settings)

print("Sales rules from loaded module:")
for i, (pattern, intent) in enumerate(recognizer._sales_rules):
    print(f"\nRule {i}: {intent}")
    print(f"  Pattern: {repr(pattern)}")
    print(f"  Length: {len(pattern)}")
    # Show actual content
    parts = pattern.split('|')
    print(f"  Parts ({len(parts)}):")
    for p in parts:
        print(f"    - '{p}'")