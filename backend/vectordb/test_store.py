"""
Test script for ChromaDB storage layer.

Stores 10 embedded Flask chunks, queries with a natural language question,
and prints top 3 results.
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chunker.ast_chunker import build_chunks_from_repo
from embeddings.embedder import embed_chunks
from vectordb.store import store_chunks, query_collection

logging.basicConfig(level=logging.INFO, format="%(message)s")

if __name__ == "__main__":
    import flask
    import os

    flask_path = Path(os.path.dirname(flask.__file__))
    if not flask_path.exists():
        print("[FAIL] Flask package not found")
        sys.exit(1)

    print("[OK] Loading 10 chunks from Flask...")
    chunks = build_chunks_from_repo(flask_path)[:10]
    if len(chunks) < 10:
        print(f"[FAIL] Expected 10 chunks, got {len(chunks)}")
        sys.exit(1)

    print("[OK] Embedding chunks with local model...")
    embedded = embed_chunks(chunks, model="local", batch_size=50)

    print("[OK] Storing in test_collection...")
    store_chunks(embedded, collection_name="test_collection", batch_size=100)

    print("[OK] Embedding query: 'how does Flask handle routing'...")
    query_chunk = [{"source": "how does Flask handle routing"}]
    query_embedded = embed_chunks(query_chunk, model="local")
    query_embedding = query_embedded[0]["embedding"]

    print("[OK] Querying collection (top 3)...")
    results = query_collection(
        query_embedding=query_embedding,
        collection_name="test_collection",
        n_results=3,
    )

    print("\n" + "=" * 70)
    print("Top 3 results for: 'how does Flask handle routing'")
    print("=" * 70)
    for i, r in enumerate(results, 1):
        meta = r.get("metadata", {})
        name = meta.get("name", "?")
        file_path = meta.get("file_path", "?")
        distance = r.get("distance", "?")
        print(f"\n{i}. {name}")
        print(f"   File: {file_path}")
        print(f"   Distance: {distance}")
    print("=" * 70)
    print("\n[OK] Test completed!")
