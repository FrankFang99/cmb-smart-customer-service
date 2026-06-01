"""Find the actual sales_rules assignment line"""
with open('src/components/intent_recognizer.py', 'rb') as f:
    content = f.read()

# Find lines with "self._sales_rules"
lines = content.split(b'\n')
for i, line in enumerate(lines):
    if b'self._sales_rules' in line:
        print(f"Line {i+1}: {line.decode('utf-8', errors='replace')}")
        print(f"  Bytes: {line.hex()[:200]}...")
        # Try to extract the pattern from this line
        start = line.find(b'_sales_rules = [')
        if start >= 0:
            # Find first opening quote after "["
            q1 = line.find(b'"', start)
            q2 = line.find(b'"', q1 + 1)
            pattern = line[q1+1:q2]
            print(f"\n  First pattern: {pattern.decode('utf-8', errors='replace')}")
        print()