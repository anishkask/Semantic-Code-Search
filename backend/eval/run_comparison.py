"""
Run OpenAI ingest, evaluate both models, and print comparison.

Ingests Flask with text-embedding-3-small into flask_openai, runs eval on both
flask_local (MiniLM) and flask_openai (OpenAI), saves results, prints comparison.
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

_backend = Path(__file__).resolve().parent.parent
for p in [_backend / ".env", Path.cwd() / ".env", Path.cwd() / "backend" / ".env"]:
    if p.exists():
        load_dotenv(p)
        break
else:
    load_dotenv(_backend / ".env")  # try anyway
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from chunker.ast_chunker import build_chunks_from_repo
from embeddings.embedder import embed_chunks
from vectordb.store import store_chunks, get_collection_count, delete_collections
from eval.evaluator import run_eval, print_eval_report

EVAL_PATH = Path(__file__).resolve().parent / "eval_set.json"
RESULTS_PATH = Path(__file__).resolve().parent / "eval_results.json"


def main():
    # Confirm OpenAI key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[FAIL] OPENAI_API_KEY not set.")
        print("  Create backend/.env with: OPENAI_API_KEY=sk-your-key")
        print("  Or copy backend/.env.example to backend/.env")
        sys.exit(1)
    print("[OK] OPENAI_API_KEY is set")
    print("[OK] Embedding 382 chunks ~$0.001 (negligible)\n")

    import flask
    flask_path = Path(os.path.dirname(flask.__file__))

    # --fresh: delete both collections and re-ingest
    if "--fresh" in sys.argv:
        print("[OK] --fresh: deleting both collections...")
        delete_collections("flask_local", "flask_openai")
        print("[OK] Deleted flask_local, flask_openai\n")

    # Load chunks once (shared by both ingests)
    chunks = None

    # Ingest flask_local (skip if exists)
    count_local = get_collection_count("flask_local")
    if count_local > 0:
        print(f"[OK] Collection 'flask_local' already has {count_local} chunks, skipping ingest")
    else:
        if chunks is None:
            print("[OK] Loading all Flask chunks...")
            chunks = build_chunks_from_repo(flask_path)
            print(f"[OK] Loaded {len(chunks)} chunks")
        print("[OK] Embedding with MiniLM (local)...")
        embedded = embed_chunks(chunks, model="local", batch_size=50)
        print("[OK] Storing in flask_local...")
        store_chunks(embedded, collection_name="flask_local", batch_size=100)
        print(f"[OK] Ingest complete: {len(embedded)} chunks stored\n")

    # Ingest flask_openai (skip if exists)
    count_openai = get_collection_count("flask_openai")
    if count_openai > 0:
        print(f"[OK] Collection 'flask_openai' already has {count_openai} chunks, skipping ingest")
    else:
        if chunks is None:
            print("[OK] Loading all Flask chunks...")
            chunks = build_chunks_from_repo(flask_path)
            print(f"[OK] Loaded {len(chunks)} chunks")
        print("[OK] Embedding with OpenAI text-embedding-3-small...")
        embedded = embed_chunks(chunks, model="openai", batch_size=50)
        print("[OK] Storing in flask_openai...")
        store_chunks(embedded, collection_name="flask_openai", batch_size=100)
        print(f"[OK] Ingest complete: {len(embedded)} chunks stored\n")

    # Run eval on both
    print("Running evaluation on flask_local (MiniLM)...")
    results_local = run_eval(EVAL_PATH, "flask_local", model="local", k_values=[1, 3, 5])
    print("Running evaluation on flask_openai (OpenAI)...")
    results_openai = run_eval(EVAL_PATH, "flask_openai", model="openai", k_values=[1, 3, 5])

    # Save results
    out = {
        "flask_local": results_local,
        "flask_openai": results_openai,
    }
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"\n[OK] Results saved to {RESULTS_PATH}\n")

    # Comparison
    per_local = results_local["per_query"]
    per_openai = results_openai["per_query"]
    k_values = [1, 3, 5]

    improved = []
    same = []
    regressed = []

    for q in per_local:
        local_hits = sum(1 for k in k_values if per_local[q][k])
        openai_hits = sum(1 for k in k_values if per_openai[q][k])
        if openai_hits > local_hits:
            improved.append(q)
        elif openai_hits == local_hits:
            same.append(q)
        else:
            regressed.append(q)

    # Print comparison table
    print("=" * 70)
    print("MODEL COMPARISON: MiniLM vs OpenAI text-embedding-3-small")
    print("=" * 70)
    print()
    print(f"{'Metric':<15} {'MiniLM (local)':<20} {'OpenAI':<20} {'Delta':<15}")
    print("-" * 70)
    for k in k_values:
        r_local = results_local["recall"][k]
        r_openai = results_openai["recall"][k]
        delta = r_openai - r_local
        sign = "+" if delta >= 0 else ""
        print(f"Recall@{k:<2}      {r_local:>6.1%} ({int(r_local*20):>2}/20)     {r_openai:>6.1%} ({int(r_openai*20):>2}/20)     {sign}{delta:.1%}")
    print("-" * 70)
    print()

    print("Query breakdown:")
    print("-" * 70)
    print(f"  Improved ({len(improved)}):")
    for q in improved:
        print(f"    + \"{q}\"")
    print(f"\n  Same ({len(same)}):")
    for q in same:
        print(f"    = \"{q}\"")
    print(f"\n  Regressed ({len(regressed)}):")
    for q in regressed:
        print(f"    - \"{q}\"")
    print()
    print("=" * 70)
    print("[OK] Comparison complete")


if __name__ == "__main__":
    main()
