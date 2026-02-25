"""
Diagnose truncation impact: run OpenAI ingest with log_truncation=True.
Shows which chunks were truncated, their names, and original character lengths.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

_backend = Path(__file__).resolve().parent.parent
for p in [_backend / ".env", Path.cwd() / ".env", Path.cwd() / "backend" / ".env"]:
    if p.exists():
        load_dotenv(p)
        break
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from chunker.ast_chunker import build_chunks_from_repo
from embeddings.embedder import embed_chunks

if __name__ == "__main__":
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[FAIL] OPENAI_API_KEY not set.")
        sys.exit(1)

    import flask
    flask_path = Path(os.path.dirname(flask.__file__))

    print("[OK] Loading all Flask chunks...")
    chunks = build_chunks_from_repo(flask_path)
    print(f"[OK] Loaded {len(chunks)} chunks")
    print("[OK] Embedding with OpenAI (log_truncation=True)...\n")

    embed_chunks(chunks, model="openai", batch_size=50, log_truncation=True)

    print("[OK] Diagnosis complete (chunks not stored)")
