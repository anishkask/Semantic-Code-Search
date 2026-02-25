"""
Test script for embed_chunks function.

Uses the local model (all-MiniLM-L6-v2) only - no OpenAI API calls.
"""

import logging
import sys
from pathlib import Path

# Add parent to path so we can import from chunker
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chunker.ast_chunker import build_chunks_from_repo
from embeddings.embedder import embed_chunks, MINILM_DIMENSION

# Enable batch progress logging
logging.basicConfig(level=logging.INFO, format="%(message)s")

if __name__ == "__main__":
    import flask
    import os

    flask_path = Path(os.path.dirname(flask.__file__))
    if not flask_path.exists():
        print("[FAIL] Flask package not found")
        sys.exit(1)

    print("[OK] Loading 10 chunks from Flask codebase...")
    chunks = build_chunks_from_repo(flask_path)
    chunks = chunks[:10]

    if len(chunks) < 10:
        print(f"[FAIL] Expected at least 10 chunks, got {len(chunks)}")
        sys.exit(1)

    print(f"[OK] Loaded {len(chunks)} chunks")
    print(f"[OK] Embedding with local model (all-MiniLM-L6-v2)...\n")

    embedded = embed_chunks(chunks, model="local", batch_size=50)

    print("\n[OK] Verifying embeddings...")

    all_valid = True
    for i, chunk in enumerate(embedded):
        if "embedding" not in chunk:
            print(f"[FAIL] Chunk {i} ({chunk.get('id', '?')}) missing 'embedding' field")
            all_valid = False
            continue
        emb = chunk["embedding"]
        if not isinstance(emb, list):
            print(f"[FAIL] Chunk {i} embedding is not a list (got {type(emb).__name__})")
            all_valid = False
            continue
        if not all(isinstance(x, float) for x in emb):
            print(f"[FAIL] Chunk {i} embedding contains non-float values")
            all_valid = False
            continue
        if len(emb) != MINILM_DIMENSION:
            print(
                f"[FAIL] Chunk {i} embedding has wrong dimension: "
                f"expected {MINILM_DIMENSION}, got {len(emb)}"
            )
            all_valid = False

    if all_valid:
        print("[OK] All chunks have valid embedding fields")

    # Print sample
    first = embedded[0]
    emb = first["embedding"]
    print(f"\n[OK] Embedding dimension: {len(emb)}")
    print(f"[OK] First 5 values: {emb[:5]}")
    print(f"[OK] Sample chunk: {first.get('id', '?')}")

    if all_valid:
        print("\n[OK] All tests passed!")
    else:
        print("\n[FAIL] Some tests failed")
        sys.exit(1)
