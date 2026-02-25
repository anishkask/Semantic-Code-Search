"""
Test script for parse_file function.

Run this to verify that parse_file correctly parses Python files.
"""

from pathlib import Path
from ast_chunker import parse_file

# Test with a simple example file
if __name__ == "__main__":
    # Create a temporary test file
    test_file = Path("test_example.py")
    
    # Write a simple Python file
    test_file.write_text("""
def hello():
    return "world"

class MyClass:
    def method(self):
        pass
""")
    
    try:
        tree = parse_file(test_file)
        print(f"✓ Successfully parsed {test_file}")
        print(f"  Type: {type(tree)}")
        print(f"  Number of top-level nodes: {len(tree.body)}")
        print(f"  Node types: {[type(node).__name__ for node in tree.body]}")
        
        # Clean up
        test_file.unlink()
        print("\n✓ Test passed!")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        # Clean up even on error
        if test_file.exists():
            test_file.unlink()
