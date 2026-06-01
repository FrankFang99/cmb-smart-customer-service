"""Find all self._sales_rules references"""
with open('src/components/intent_recognizer.py', 'rb') as f:
    content = f.read()

# Search for "_sales_rules"
search = b'_sales_rules'
pos = 0
while True:
    pos = content.find(search, pos)
    if pos < 0:
        break
    # Show context around this position
    start = max(0, pos - 30)
    end = min(len(content), pos + 60)
    context = content[start:end]
    print(f"Found at byte {pos}:")
    print(f"  Context: {context.decode('utf-8', errors='replace')}")
    print()
    pos += 1