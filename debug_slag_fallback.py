from parse_thumbnail_txt import parse_file
import os

# Create a dummy file with empty content to test fallback
with open("test_empty.txt", "w") as f:
    f.write("")

# Create a dummy file with empty lines
with open("test_newlines.txt", "w") as f:
    f.write("\n\n\n")

print("--- Testing empty file ---")
res1 = parse_file("test_empty.txt")
print(f"Slag: '{res1['slag']}'")

print("\n--- Testing newlines file ---")
res2 = parse_file("test_newlines.txt")
print(f"Slag: '{res2['slag']}'")

# Clean up
try:
    os.remove("test_empty.txt")
    os.remove("test_newlines.txt")
except:
    pass
