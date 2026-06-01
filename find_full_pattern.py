"""Find the FULL pattern for sales_rules"""
with open('src/components/intent_recognizer.py', 'rb') as f:
    content = f.read()

# Find the first self._sales_rules assignment
search = b'self._sales_rules = ['
pos = content.find(search)
if pos < 0:
    print("Not found")
else:
    # Get 500 bytes after this to capture the first pattern
    chunk = content[pos:pos+500]
    print(f"Chunk hex (first 300 bytes):")
    print(chunk[:300].hex())

    # Find the first pattern - look for the first quote after "["
    bracket_pos = chunk.find(b'[')
    first_quote = chunk.find(b'"', bracket_pos)
    second_quote = chunk.find(b'"', first_quote + 1)
    pattern = chunk[first_quote+1:second_quote]
    print(f"\nFirst pattern extracted:")
    print(f"  Hex: {pattern.hex()}")
    print(f"  Length: {len(pattern)}")

    # Decode character by character
    print(f"\n  Decoded (char by char):")
    i = 0
    while i < len(pattern):
        char_bytes = pattern[i:i+3] if i+3 <= len(pattern) else pattern[i:]
        try:
            char = char_bytes.decode('utf-8')
            print(f"    {char_bytes.hex()} -> {char}")
        except:
            print(f"    {char_bytes.hex()} -> (error)")
        i += 3 if i+3 <= len(pattern) else 1