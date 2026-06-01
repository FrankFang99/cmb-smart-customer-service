"""Debug pattern matching byte by byte"""
import re

# Direct test
text = "有什么好理财"
pattern = r"好.*理财"

print(f"Text: '{text}'")
print(f"Text bytes: {text.encode('utf-8').hex()}")
print(f"Pattern: '{pattern}'")
print(f"Pattern bytes: {pattern.encode('utf-8').hex()}")
print()

match = re.search(pattern, text)
print(f"Match result: {match}")
if match:
    print(f"Matched: '{match.group()}'")

print()
print("Trying full pattern:")
pattern2 = r"推荐.*理财|理财推荐|想买理财|好.*理财|有什么好"
match2 = re.search(pattern2, text)
print(f"Match result: {match2}")
if match2:
    print(f"Matched: '{match2.group()}'")