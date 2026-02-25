"""
Test script to verify error handling in build_chunks_from_repo.

Tests that files with syntax errors are skipped gracefully.
"""

from pathlib import Path
from ast_chunker import build_chunks_from_repo, print_chunk_summary
import tempfile
import os

# Test error handling with a directory containing both valid and invalid Python files
if __name__ == "__main__":
    # Create a temporary test directory
    test_dir = Path("test_repo_error_handling")
    test_dir.mkdir(exist_ok=True)
    
    # Create valid Python files
    (test_dir / "valid1.py").write_text("""
def function_one():
    return "hello"

class MyClass:
    def method(self):
        return "world"
""")
    
    (test_dir / "valid2.py").write_text("""
def function_two():
    return "test"
""")
    
    # Create invalid Python file (syntax error)
    (test_dir / "invalid.py").write_text("""
def broken_function(
    # Missing closing parenthesis and body
""")
    
    # Create another invalid file (missing colon)
    (test_dir / "invalid2.py").write_text("""
def broken()
    return "error"
""")
    
    try:
        print(f"[OK] Testing error handling with test directory: {test_dir}")
        print(f"[OK] Created test files (2 valid, 2 invalid)\n")
        
        # Build chunks from repository (should skip invalid files)
        chunks = build_chunks_from_repo(test_dir)
        
        print(f"[OK] Successfully processed test repository")
        print(f"[OK] Total chunks collected: {len(chunks)}")
        print(f"[OK] Expected: 3 chunks (1 function, 1 class, 1 method)")
        
        # Verify we got the expected chunks
        expected_chunks = {
            "valid1.py::function_one",
            "valid1.py::MyClass",
            "valid1.py::method",
            "valid2.py::function_two"
        }
        
        actual_chunks = {chunk["id"] for chunk in chunks}
        
        if actual_chunks == expected_chunks:
            print(f"[OK] All expected chunks found!")
        else:
            print(f"[FAIL] Mismatch:")
            print(f"  Expected: {expected_chunks}")
            print(f"  Actual: {actual_chunks}")
        
        # Print summary
        print("\n")
        print_chunk_summary(chunks)
        
        print(f"\n[OK] Error handling test completed!")
        print(f"[OK] Invalid files were skipped gracefully (no crash)")
        
        # Clean up
        import shutil
        shutil.rmtree(test_dir)
        
    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        # Clean up even on error
        if test_dir.exists():
            import shutil
            shutil.rmtree(test_dir)
