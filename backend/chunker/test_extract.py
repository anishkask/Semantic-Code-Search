"""
Test script for extract_source function.

Run this to verify that extract_source correctly extracts source code including decorators.
"""

from pathlib import Path
from ast_chunker import parse_file, extract_source
import ast

# Test with various decorated and undecorated constructs
if __name__ == "__main__":
    # Create a temporary test file with various constructs
    test_file = Path("test_extract_example.py")
    
    # Write a Python file with:
    # - Plain function (no decorator)
    # - Decorated function (single decorator)
    # - Function with multiple decorators
    # - Function with multi-line decorator
    # - Class with decorator
    test_file.write_text("""def plain_function():
    '''A plain function without decorators.'''
    return "hello"

@decorator
def decorated_function():
    '''A function with a single decorator.'''
    return "world"

@decorator1
@decorator2
def multi_decorated_function():
    '''A function with multiple decorators.'''
    return "test"

@multi_line_decorator(
    arg1="value1",
    arg2="value2"
)
def multi_line_decorated_function():
    '''A function with a multi-line decorator.'''
    return "multi"

@class_decorator
class DecoratedClass:
    '''A class with a decorator.'''
    
    def method(self):
        pass
""")
    
    try:
        # Parse the file
        tree = parse_file(test_file)
        source_code = test_file.read_text()
        print(f"[OK] Successfully parsed {test_file}\n")
        
        # Find nodes by traversing
        nodes_found = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                # Only get top-level nodes (not methods or nested functions)
                if node.lineno <= 30:  # Our test constructs are in first 30 lines
                    nodes_found.append(node)
        
        # Sort by line number for consistent testing
        nodes_found.sort(key=lambda n: n.lineno)
        
        print("Testing source extraction:")
        print("=" * 70)
        
        # Test 1: Plain function
        plain_func = nodes_found[0]
        assert plain_func.name == "plain_function", f"Expected plain_function, got {plain_func.name}"
        extracted = extract_source(plain_func, source_code)
        print("\n1. Plain function (no decorator):")
        print("-" * 70)
        print(extracted)
        assert "@" not in extracted, "Plain function should not have decorators"
        assert "def plain_function():" in extracted, "Should contain function definition"
        print("[OK] Plain function extraction correct")
        
        # Test 2: Decorated function
        decorated_func = nodes_found[1]
        assert decorated_func.name == "decorated_function", f"Expected decorated_function, got {decorated_func.name}"
        extracted = extract_source(decorated_func, source_code)
        print("\n2. Decorated function (single decorator):")
        print("-" * 70)
        print(extracted)
        assert "@decorator" in extracted, "Should contain decorator"
        assert "def decorated_function():" in extracted, "Should contain function definition"
        assert extracted.strip().startswith("@decorator"), "Should start with decorator"
        print("[OK] Decorated function extraction correct")
        
        # Test 3: Multi-decorated function
        multi_decorated_func = nodes_found[2]
        assert multi_decorated_func.name == "multi_decorated_function", f"Expected multi_decorated_function, got {multi_decorated_func.name}"
        extracted = extract_source(multi_decorated_func, source_code)
        print("\n3. Multi-decorated function:")
        print("-" * 70)
        print(extracted)
        assert "@decorator1" in extracted, "Should contain first decorator"
        assert "@decorator2" in extracted, "Should contain second decorator"
        assert "def multi_decorated_function():" in extracted, "Should contain function definition"
        assert extracted.strip().startswith("@decorator1"), "Should start with first decorator"
        print("[OK] Multi-decorated function extraction correct")
        
        # Test 4: Multi-line decorator
        multi_line_func = nodes_found[3]
        assert multi_line_func.name == "multi_line_decorated_function", f"Expected multi_line_decorated_function, got {multi_line_func.name}"
        extracted = extract_source(multi_line_func, source_code)
        print("\n4. Multi-line decorated function:")
        print("-" * 70)
        print(extracted)
        assert "@multi_line_decorator" in extracted, "Should contain decorator name"
        assert "arg1=\"value1\"" in extracted, "Should contain decorator arguments"
        assert "arg2=\"value2\"" in extracted, "Should contain decorator arguments"
        assert "def multi_line_decorated_function():" in extracted, "Should contain function definition"
        print("[OK] Multi-line decorated function extraction correct")
        
        # Test 5: Decorated class
        decorated_class = nodes_found[4]
        assert decorated_class.name == "DecoratedClass", f"Expected DecoratedClass, got {decorated_class.name}"
        extracted = extract_source(decorated_class, source_code)
        print("\n5. Decorated class:")
        print("-" * 70)
        print(extracted)
        assert "@class_decorator" in extracted, "Should contain decorator"
        assert "class DecoratedClass:" in extracted, "Should contain class definition"
        assert extracted.strip().startswith("@class_decorator"), "Should start with decorator"
        print("[OK] Decorated class extraction correct")
        
        print("\n" + "=" * 70)
        print("[OK] All tests passed!")
        
        # Clean up
        test_file.unlink()
        print("\n[OK] Test completed!")
        
    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        # Clean up even on error
        if test_file.exists():
            test_file.unlink()
