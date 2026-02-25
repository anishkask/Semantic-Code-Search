"""
Test script for build_chunks_from_file function with decorated functions.

Run this to verify that build_chunks_from_file correctly handles decorators.
"""

from pathlib import Path
from ast_chunker import build_chunks_from_file
import tempfile
import os

# Test with a file containing decorated functions
if __name__ == "__main__":
    # Create a temporary test file with decorated functions
    test_file = Path("test_decorated_example.py")
    
    test_file.write_text("""import functools

def plain_function():
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
    
    def plain_method(self):
        return "method"
    
    @method_decorator
    def decorated_method(self):
        return "decorated"
""")
    
    try:
        # Use current directory as repo root
        repo_root = Path(".")
        
        print(f"[OK] Testing with test file: {test_file}")
        print(f"[OK] Repo root: {repo_root.absolute()}\n")
        
        # Build chunks from the file
        chunks = build_chunks_from_file(test_file, repo_root)
        
        print(f"[OK] Successfully built {len(chunks)} chunks\n")
        print("=" * 80)
        print("All chunks:")
        print("=" * 80)
        
        # Print all chunks with all fields visible
        for i, chunk in enumerate(chunks, 1):
            print(f"\nChunk {i}:")
            print("-" * 80)
            print(f"  id:           {chunk['id']}")
            print(f"  name:         {chunk['name']}")
            print(f"  type:         {chunk['type']}")
            print(f"  file_path:    {chunk['file_path']}")
            print(f"  start_line:   {chunk['start_line']}")
            print(f"  end_line:     {chunk['end_line']}")
            print(f"  parent_class: '{chunk['parent_class']}'")
            print(f"  source (first 5 lines):")
            source_lines = chunk['source'].split('\n')
            for j, line in enumerate(source_lines[:5], 1):
                print(f"    {j:3d}: {line}")
            if len(source_lines) > 5:
                print(f"    ... ({len(source_lines) - 5} more lines)")
        
        print("\n" + "=" * 80)
        
        # Verify decorator handling
        print("\nVerifying decorator handling...")
        
        # Check decorated_function
        decorated_func = next((c for c in chunks if c['name'] == 'decorated_function'), None)
        if decorated_func:
            if decorated_func['start_line'] < decorated_func['source'].find('def decorated_function'):
                # Count lines before 'def' in source
                lines_before_def = decorated_func['source'].split('def decorated_function')[0].count('\n')
                if lines_before_def > 0:
                    print(f"[OK] decorated_function has decorator (start_line accounts for decorator)")
                else:
                    print(f"[FAIL] decorated_function should have decorator but source doesn't show it")
            if '@decorator' in decorated_func['source']:
                print(f"[OK] decorated_function source includes decorator")
            else:
                print(f"[FAIL] decorated_function source missing decorator")
        
        # Check multi_decorated_function
        multi_decorated = next((c for c in chunks if c['name'] == 'multi_decorated_function'), None)
        if multi_decorated:
            if '@decorator1' in multi_decorated['source'] and '@decorator2' in multi_decorated['source']:
                print(f"[OK] multi_decorated_function includes both decorators")
            else:
                print(f"[FAIL] multi_decorated_function missing decorators")
        
        # Check multi_line_decorated_function
        multi_line = next((c for c in chunks if c['name'] == 'multi_line_decorated_function'), None)
        if multi_line:
            if '@multi_line_decorator' in multi_line['source'] and 'arg1="value1"' in multi_line['source']:
                print(f"[OK] multi_line_decorated_function includes multi-line decorator")
            else:
                print(f"[FAIL] multi_line_decorated_function missing decorator content")
        
        # Check decorated_method
        decorated_method = next((c for c in chunks if c['name'] == 'decorated_method'), None)
        if decorated_method:
            if decorated_method['type'] == 'method' and decorated_method['parent_class'] == 'DecoratedClass':
                print(f"[OK] decorated_method correctly identified as method")
            if '@method_decorator' in decorated_method['source']:
                print(f"[OK] decorated_method source includes decorator")
            else:
                print(f"[FAIL] decorated_method source missing decorator")
        
        # Check plain_function (should not have decorator)
        plain_func = next((c for c in chunks if c['name'] == 'plain_function'), None)
        if plain_func:
            if '@' not in plain_func['source']:
                print(f"[OK] plain_function correctly has no decorator")
            else:
                print(f"[FAIL] plain_function should not have decorator")
        
        print(f"\n[OK] Test completed! Total chunks: {len(chunks)}")
        
        # Clean up
        test_file.unlink()
        
    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        # Clean up even on error
        if test_file.exists():
            test_file.unlink()
