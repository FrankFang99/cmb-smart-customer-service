"""Debug why the pattern doesn't match"""
import re

# Test with hardcoded pattern
pattern1 = r"好.*理财"
text = "有什么好理财"
match1 = re.search(pattern1, text)
print(f"Hardcoded pattern '{pattern1}' matches '{text}': {match1}")

# Test with pattern from file
with open('src/components/intent_recognizer.py', 'rb') as f:
    content = f.read()

# Find the sales_wealth_prod line
import re
pattern_bytes = b'\xe5\xa5\xbd\x2e\x2a\xe7\x90\x86\xe8\xb4\xa2'  # 好.*理财 in bytes
idx = content.find(pattern_bytes)
if idx >= 0:
    print(f"\nFound '好.*理财' in file at byte {idx}")
    # Get the full line
    line_start = content.rfind(b'\n', 0, idx) + 1
    line_end = content.find(b'\n', idx)
    line = content[line_start:line_end]
    print(f"Line: {line.decode('utf-8', errors='replace')}")

    # Extract the pattern string
    quote_start = line.find(b'"')
    quote_end = line.rfind(b'"')
    pattern_str = line[quote_start+1:quote_end].decode('utf-8', errors='replace')
    print(f"Extracted pattern: '{pattern_str}'")
    print(f"Pattern repr: {repr(pattern_str)}")

    # Test it
    match2 = re.search(pattern_str, text)
    print(f"Match with extracted pattern: {match2}")
else:
    print("'好.*理财' not found in file")