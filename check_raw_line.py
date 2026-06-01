"""Check raw bytes of the sales_rules line"""
# Read file as binary
with open('src/components/intent_recognizer.py', 'rb') as f:
    content = f.read()

# Find the line containing "sales_wealth_prod"
lines = content.split(b'\n')
for i, line in enumerate(lines):
    if b'sales_wealth_prod' in line:
        print(f"Line {i+1}:")
        print(f"  Raw bytes: {line.hex()}")
        print(f"  Decoded (errors=replace): {line.decode('utf-8', errors='replace')}")
        # Find the pattern part
        # Look for the opening quote of the pattern
        start = line.find(b'(r"') + 3
        end = line.find(b'",', start)
        pattern_bytes = line[start:end]
        print(f"\n  Pattern bytes: {pattern_bytes.hex()}")
        print(f"  Pattern decoded: {pattern_bytes.decode('utf-8', errors='replace')}")
        break