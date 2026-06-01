"""Compare file pattern vs loaded pattern"""
import re

# Get pattern from file
with open('src/components/intent_recognizer.py', 'rb') as f:
    content = f.read()

# Find sales_wealth_prod line
line_start = content.find(b'sales_wealth_prod')
line_end = content.find(b'\n', line_start)
line = content[line_start:line_end]

# Extract pattern
quote_start = line.find(b'"')
quote_end = line.rfind(b'"')
file_pattern = line[quote_start+1:quote_end].decode('utf-8', errors='replace')

print(f"File pattern: '{file_pattern}'")
print(f"File pattern bytes: {file_pattern.encode('utf-8').hex()}")

# Get pattern from IntentRecognizer
from src.components.intent_recognizer import IntentRecognizer
from src.config import settings

recognizer = IntentRecognizer(settings)
loaded_pattern = recognizer._sales_rules[0][0]

print(f"\nLoaded pattern: '{loaded_pattern}'")
print(f"Loaded pattern bytes: {loaded_pattern.encode('utf-8').hex()}")

print(f"\nAre they equal: {file_pattern == loaded_pattern}")
print(f"File pattern len: {len(file_pattern)}")
print(f"Loaded pattern len: {len(loaded_pattern)}")