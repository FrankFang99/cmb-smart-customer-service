"""Compare file pattern vs loaded pattern - fixed"""
import re

# Get pattern from file
with open('src/components/intent_recognizer.py', 'rb') as f:
    content = f.read()

# Find sales_wealth_prod line - search backwards for the start of the tuple
sales_pos = content.find(b'sales_wealth_prod')
# Go backwards to find the opening (
paren_start = content.rfind(b'(', 0, sales_pos)
# Find the first quote after (
quote_start = content.find(b'"', paren_start)
# Find the second quote (closing the pattern)
quote_end = content.find(b'"', quote_start + 1)

file_pattern = content[quote_start+1:quote_end].decode('utf-8', errors='replace')

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

# Show the difference
print(f"\nFile pattern length: {len(file_pattern)}")
print(f"Loaded pattern length: {len(loaded_pattern)}")

# Check if loaded pattern is actually the first 3 options
if "推荐" in loaded_pattern and "理财推荐" in loaded_pattern and "想买理财" in loaded_pattern:
    print("\nLoaded pattern appears to be truncated - only 3 options instead of 5")