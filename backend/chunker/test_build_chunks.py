"""
Test script for build_chunks_from_file function.

Run this to verify that build_chunks_from_file correctly builds chunks from a Python file.
Tests against Flask's app.py which has decorated methods, plain functions, and classes.
"""

from pathlib import Path
from ast_chunker import build_chunks_from_file
import flask
import os

# Test with Flask's app.py
if __name__ == "__main__":
    # Get Flask's app.py path
    flask_path = Path(os.path.dirname(flask.__file__))
    app_py_path = flask_path / "app.py"
    repo_root = flask_path  # Flask package directory as repo root
    
    if not app_py_path.exists():
        print(f"[FAIL] Flask app.py not found at {app_py_path}")
        exit(1)
    
    try:
        print(f"[OK] Testing with Flask app.py: {app_py_path}")
        print(f"[OK] Repo root: {repo_root}\n")
        
        # Build chunks from the file
        chunks = build_chunks_from_file(app_py_path, repo_root)
        
        print(f"[OK] Successfully built {len(chunks)} chunks\n")
        print("=" * 80)
        print("First 5 chunks:")
        print("=" * 80)
        
        # Print first 5 chunks with all fields visible
        for i, chunk in enumerate(chunks[:5], 1):
            print(f"\nChunk {i}:")
            print("-" * 80)
            print(f"  id:           {chunk['id']}")
            print(f"  name:         {chunk['name']}")
            print(f"  type:         {chunk['type']}")
            print(f"  file_path:    {chunk['file_path']}")
            print(f"  start_line:   {chunk['start_line']}")
            print(f"  end_line:     {chunk['end_line']}")
            print(f"  parent_class: '{chunk['parent_class']}'")
            print(f"  source:")
            # Print source with indentation, limit to first 10 lines
            source_lines = chunk['source'].split('\n')
            for j, line in enumerate(source_lines[:10], 1):
                print(f"    {j:3d}: {line}")
            if len(source_lines) > 10:
                print(f"    ... ({len(source_lines) - 10} more lines)")
        
        print("\n" + "=" * 80)
        
        # Verify chunk structure
        print("\nVerifying chunk structure...")
        all_valid = True
        required_fields = ["id", "name", "type", "source", "file_path", "start_line", "end_line", "parent_class"]
        
        for chunk in chunks:
            for field in required_fields:
                if field not in chunk:
                    print(f"[FAIL] Missing field '{field}' in chunk: {chunk.get('name', 'unknown')}")
                    all_valid = False
        
        # Verify IDs are unique
        ids = [chunk['id'] for chunk in chunks]
        if len(ids) != len(set(ids)):
            print("[FAIL] Duplicate IDs found!")
            all_valid = False
        else:
            print("[OK] All IDs are unique")
        
        # Verify IDs follow the pattern filepath::name
        for chunk in chunks:
            if "::" not in chunk['id']:
                print(f"[FAIL] Invalid ID format: {chunk['id']}")
                all_valid = False
        
        # Check for different types
        types_found = set(chunk['type'] for chunk in chunks)
        print(f"\n[OK] Types found: {types_found}")
        
        # Check for methods with parent_class
        methods = [chunk for chunk in chunks if chunk['type'] == 'method']
        methods_with_parent = [chunk for chunk in methods if chunk['parent_class']]
        print(f"[OK] Methods found: {len(methods)}")
        print(f"[OK] Methods with parent_class: {len(methods_with_parent)}")
        
        # Check for decorated functions (start_line != def line would indicate decorator)
        # We can't easily check this without parsing, but we can verify start_line <= end_line
        for chunk in chunks:
            if chunk['start_line'] > chunk['end_line']:
                print(f"[FAIL] Invalid line range for {chunk['name']}: {chunk['start_line']} > {chunk['end_line']}")
                all_valid = False
        
        if all_valid:
            print("\n[OK] All chunk structure validations passed!")
        else:
            print("\n[FAIL] Some validations failed!")
        
        print(f"\n[OK] Test completed! Total chunks: {len(chunks)}")
        
    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
