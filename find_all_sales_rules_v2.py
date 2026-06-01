"""Find all self._sales_rules references - write to file"""
with open('src/components/intent_recognizer.py', 'rb') as f:
    content = f.read()

output = []

# Search for "_sales_rules"
search = b'_sales_rules'
pos = 0
count = 0
while True:
    pos = content.find(search, pos)
    if pos < 0:
        break
    # Show context around this position
    start = max(0, pos - 30)
    end = min(len(content), pos + 60)
    context = content[start:end]
    count += 1
    output.append(f"Found at byte {pos}:")
    output.append(f"  Context (hex): {context.hex()}")
    output.append("")
    pos += 1

output.insert(0, f"Total occurrences: {count}")

with open('debug_output.txt', 'w', encoding='utf-8') as f:
    f.write("\n".join(output))

print("Written to debug_output.txt")