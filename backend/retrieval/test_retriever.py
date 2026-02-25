"""
Test script for the retrieval layer.

Runs full ingest of Flask codebase (if needed) and executes 5 search queries.
First run: ~1-2 minutes for embedding 382 chunks. Subsequent runs: skip ingest.
"""

import sys
from pathlib import Path

# Ensure backend is on path for imports
_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from chunker.ast_chunker import build_chunks_from_repo
from embeddings.embedder import embed_chunks
from vectordb.store import store_chunks, get_collection_count
from retrieval.retriever import search

COLLECTION_NAME = "flask_local"

QUERIES = [
    "how does Flask handle routing",
    "where is the request context created",
    "how are blueprints registered",
    "where does Flask handle errors and exceptions",
    "how does Flask initialize the application",
]

if __name__ == "__main__":
    import flask
    import os

    flask_path = Path(os.path.dirname(flask.__file__))
    if not flask_path.exists():
        print("[FAIL] Flask package not found")
        sys.exit(1)

    # Ingest: skip if collection already has data
    count = get_collection_count(COLLECTION_NAME)
    if count > 0:
        print(f"[OK] Collection '{COLLECTION_NAME}' already has {count} chunks, skipping ingest")
    else:
        print("[OK] Loading all Flask chunks...")
        chunks = build_chunks_from_repo(flask_path)
        print(f"[OK] Loaded {len(chunks)} chunks")
        print("[OK] Embedding with local model (this may take 1-2 minutes)...")
        embedded = embed_chunks(chunks, model="local", batch_size=50)
        print("[OK] Storing in collection...")
        store_chunks(embedded, collection_name=COLLECTION_NAME, batch_size=100)
        print(f"[OK] Ingest complete: {len(embedded)} chunks stored")

    # Run queries
    print("\n" + "=" * 70)
    print("SEARCH RESULTS")
    print("=" * 70)

    for q in QUERIES:
        print(f"\nQuery: \"{q}\"")
        print("-" * 70)
        results = search(q, collection_name=COLLECTION_NAME, model="local", n_results=3)
        for rank, r in enumerate(results, 1):
            name = r.get("name", "?")
            type_ = r.get("type", "?")
            file_path = r.get("file_path", "?")
            distance = r.get("distance", "?")
            print(f"  {rank}. {name} ({type_}) | {file_path} | distance: {distance}")
        print()

    print("=" * 70)
    print("[OK] Test completed!")
