# Find the actual pattern line
with open('src/components/intent_recognizer.py', 'rb') as f:
    content = f.read()

# Search for the pattern starting with 有什么好
target = "有什么好".encode('utf-8')
print(f"Searching for: {target.hex()}")

idx = content.find(target)
if idx >= 0:
    print(f"Found '有什么好' at byte {idx}")
else:
    print("'有什么好' NOT found in raw file")

# Also search for the full pattern 好.*理财
target2 = "好.*理财".encode('utf-8')
print(f"\nSearching for '好.*理财': {target2.hex()}")
idx2 = content.find(target2)
if idx2 >= 0:
    print(f"Found '好.*理财' at byte {idx2}")
else:
    print("'好.*理财' NOT found")