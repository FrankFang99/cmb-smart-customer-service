"""Extract the full sales_rules pattern by finding all quotes"""
with open('src/components/intent_recognizer.py', 'rb') as f:
    content = f.read()

# Find the first self._sales_rules assignment
search = b'self._sales_rules = ['
pos = content.find(search)
if pos < 0:
    print("Not found")
else:
    # Get 1000 bytes after this
    chunk = content[pos:pos+1000]

    # Find all quote positions
    quotes = []
    for i, b in enumerate(chunk):
        if b == ord('"'):
            quotes.append(i)

    print(f"Quote positions: {quotes[:20]}")

    # The pattern should be between quotes[0] and quotes[1]
    if len(quotes) >= 2:
        pattern = chunk[quotes[0]+1:quotes[1]]
        print(f"\nFirst pattern:")
        print(f"  Length: {len(pattern)}")
        print(f"  Hex: {pattern.hex()}")
        print(f"  Decoded: {pattern.decode('utf-8', errors='replace')}")

        # Check if it contains all 5 options
        parts = pattern.split(b'|')
        print(f"  Number of parts: {len(parts)}")
        for i, p in enumerate(parts):
            print(f"    {i}: {p.decode('utf-8', errors='replace')}")