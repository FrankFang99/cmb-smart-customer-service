"""Remove duplicate _sales_rules definition"""
with open('src/components/intent_recognizer.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find and remove the duplicate _sales_rules definition (lines 459-468)
# Keep everything up to line 458, then skip to line 469
output_lines = []
skip_mode = False

for i, line in enumerate(lines):
    line_num = i + 1  # 1-indexed

    # Check if this is the start of the duplicate _sales_rules
    if '        # 营销咨询规则（sales系列）' in line or (skip_mode and line.strip().startswith('#')):
        if not skip_mode:
            skip_mode = True
            continue

    # If we were skipping and hit a comment block, stop skipping
    if skip_mode and line.strip().startswith('#') and not 'sales' in line.lower():
        skip_mode = False

    # If we're in skip mode and it's an empty line, skip it
    if skip_mode and line.strip() == '':
        continue

    # If we're in skip mode and it's another _sales_rules = [, skip it
    if skip_mode and 'self._sales_rules = [' in line:
        # Skip until we find the closing ]
        continue

    if not skip_mode:
        output_lines.append(line)

# Write back
with open('src/components/intent_recognizer.py', 'w', encoding='utf-8') as f:
    f.writelines(output_lines)

print(f"Removed duplicate. New line count: {len(output_lines)}")