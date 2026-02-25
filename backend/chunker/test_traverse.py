"""
Test script for traverse_ast function.

Run this to verify that traverse_ast correctly identifies functions, classes, and methods.
"""

from pathlib import Path
from ast_chunker import parse_file, traverse_ast

# Test with a comprehensive example file
if __name__ == "__main__":
    # Create a temporary test file with various constructs
    test_file = Path("test_traverse_example.py")
    
    # Write a Python file with:
    # - Module-level imports (should be skipped)
    # - Module-level assignments (should be skipped)
    # - Module-level functions
    # - Classes with methods
    # - Nested functions (should be skipped)
    test_file.write_text("""
import os
from typing import List

CONSTANT = 42

def module_function():
    '''A module-level function.'''
    return "hello"

def another_function():
    '''Another module-level function with a nested function.'''
    def nested_function():
        return "nested"
    return nested_function()

class MyClass:
    '''A class definition.'''
    
    def method_one(self):
        '''A method.'''
        return 1
    
    def method_two(self):
        '''Another method with a nested function.'''
        def helper():
            return "help"
        return helper()

class AnotherClass:
    '''Another class.'''
    
    def class_method(self):
        pass
""")
    
    try:
        # Parse the file
        tree = parse_file(test_file)
        print(f"[OK] Successfully parsed {test_file}\n")
        
        # Traverse the AST
        nodes = traverse_ast(tree)
        
        print("Identified nodes:")
        print("-" * 50)
        for name, node_type, line_num in nodes:
            print(f"{name:20s} ({node_type:8s}) at line {line_num}")
        
        print("-" * 50)
        print(f"\nTotal nodes found: {len(nodes)}")
        
        # Verify expected results
        # Note: Line numbers are based on the actual parsed file
        expected = {
            ("module_function", "function", 7),
            ("another_function", "function", 11),
            ("MyClass", "class", 17),
            ("method_one", "method", 20),
            ("method_two", "method", 24),
            ("AnotherClass", "class", 30),
            ("class_method", "method", 33),
        }
        
        actual = set(nodes)
        if actual == expected:
            print("\n[OK] All expected nodes found!")
        else:
            print("\n[FAIL] Mismatch detected:")
            print(f"  Expected: {expected}")
            print(f"  Actual: {actual}")
            missing = expected - actual
            extra = actual - expected
            if missing:
                print(f"  Missing: {missing}")
            if extra:
                print(f"  Extra: {extra}")
        
        # Verify nested functions are NOT included
        nested_functions = [n for n in nodes if "nested" in n[0].lower() or "helper" in n[0].lower()]
        if nested_functions:
            print(f"\n[FAIL] ERROR: Nested functions should not be included, but found: {nested_functions}")
        else:
            print("\n[OK] Nested functions correctly excluded")
        
        # Clean up
        test_file.unlink()
        print("\n[OK] Test completed!")
        
    except Exception as e:
        print(f"[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        # Clean up even on error
        if test_file.exists():
            test_file.unlink()
