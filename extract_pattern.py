"""Correctly extract the actual pattern from the file"""
import re

# Read the file as text
with open('src/components/intent_recognizer.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find line 430
line = lines[429]  # 0-indexed, so line 430 is index 429
print(f"Line 430: {repr(line)}")

# The pattern should be between the first (r" and the first ",
# Find the start
start = line.find('(r"') + 3
end = line.find('",', start)
pattern = line[start:end]

print(f"\nExtracted pattern: {repr(pattern)}")
print(f"Pattern content: {pattern}")

# Check if pattern contains 好.*理财
if '好.*理财' in pattern:
    print("\nPattern DOES contain '好.*理财'")
else:
    print("\nPattern DOES NOT contain '好.*理财'")