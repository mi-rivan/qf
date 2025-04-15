from qf import decoher

# Enable the interactive error handling
decoher.enable()

# Test 1: Syntax Error
print("Test 1: Syntax Error")
eval("1+2+3+")

# Test 2: Indentation Error
print("\nTest 2: Indentation Error")
exec("""
def test_function():
    print("This is properly indented")
  print("This has incorrect indentation")
""")

# Test 3: Name Error
print("\nTest 3: Name Error")
nonexistent_variable + 5  # Variable doesn't exist

# Test 4: Type Error
print("\nTest 4: Type Error")
"string" + 5  # Can't add string and integer

# Test 5: Zero Division Error
print("\nTest 5: Zero Division Error")
result = 10 / 0  # Division by zero

# Test 6: Whitespace Issues
print("\nTest 6: Whitespace Issues")
exec("""
def mixed_whitespace():
	print("This uses tabs")
    print("This uses spaces")
""")

# Disable the interactive error handling
decoher.disable()

# Show fix history
print("\nShowing fix history:")
decoher.show_fix_history()
