# Read raw bytes from file
with open('src/components/intent_recognizer.py', 'rb') as f:
    content = f.read()

# Find the line with sales_rules
lines = content.split(b'\n')
for i, line in enumerate(lines):
    if b'sales_wealth_prod' in line:
        print(f'Line {i}: {line.hex()}')
        # Show the first pattern part
        pattern_start = line.find(b'("')
        if pattern_start >= 0:
            pattern_end = line.find(b'",', pattern_start)
            pattern_bytes = line[pattern_start+2:pattern_end]
            print(f'Pattern bytes: {pattern_bytes.hex()}')
            print(f'Pattern decoded: {pattern_bytes.decode("utf-8", errors="replace")}')
        break