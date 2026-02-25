"""
Test script for build_chunks_from_repo and print_chunk_summary functions.

Run this to verify that build_chunks_from_repo correctly processes an entire repository
and that print_chunk_summary provides useful statistics.
Tests against the entire Flask package.
"""

from pathlib import Path
from ast_chunker import build_chunks_from_repo, print_chunk_summary
import flask
import os

# Test with entire Flask package
if __name__ == "__main__":
    # Get Flask package path
    flask_path = Path(os.path.dirname(flask.__file__))
    
    if not flask_path.exists():
        print(f"[FAIL] Flask package not found at {flask_path}")
        exit(1)
    
    try:
        print(f"[OK] Testing with Flask package: {flask_path}")
        print(f"[OK] Processing all Python files...\n")
        
        # Build chunks from entire repository
        chunks = build_chunks_from_repo(flask_path)
        
        print(f"[OK] Successfully processed Flask package")
        print(f"[OK] Total chunks collected: {len(chunks)}\n")
        
        # Print summary
        print_chunk_summary(chunks)
        
        print(f"\n[OK] Test completed!")
        
    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
