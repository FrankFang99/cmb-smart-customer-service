#!/usr/bin/env python3
"""Fix encoding script"""
with open('app.py', 'rb') as f:
    data = f.read()

# Check what encoding the raw bytes represent
# If it's not UTF-8, we need to convert

# Try to detect the original encoding by finding Chinese text patterns
# Chinese in GBK: 0x81-0xFE for both bytes
# Chinese in UTF-8: 0xE0-0xEF for first byte, then 0x80-0xBF for following bytes

has_utf8_pattern = False
for i in range(len(data)-2):
    if 0xE0 <= data[i] <= 0xEF and 0x80 <= data[i+1] <= 0xBF and 0x80 <= data[i+2] <= 0xBF:
        has_utf8_pattern = True
        break

has_gbk_pattern = False
for i in range(len(data)-1):
    if 0x81 <= data[i] <= 0xFE and 0x40 <= data[i+1] <= 0xFE:
        has_gbk_pattern = True
        break

print(f"Has UTF-8 pattern: {has_utf8_pattern}")
print(f"Has GBK pattern: {has_gbk_pattern}")

# If it's GBK, convert to UTF-8
if has_gbk_pattern and not has_utf8_pattern:
    text = data.decode('gbk')
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(text)
    print("Converted from GBK to UTF-8")
else:
    print("File might already be UTF-8 or corrupted")
    # Check the first Chinese character
    print("First 100 chars raw:", data[:100])