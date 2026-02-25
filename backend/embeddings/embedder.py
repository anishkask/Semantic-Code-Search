"""
Embedding pipeline for semantic code search.

Takes chunks from the chunker and returns them with embedding vectors attached,
ready for storage in ChromaDB or similar vector stores.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any  # Any for model type hint

from dotenv import load_dotenv

# Load .env from backend/ (parent of embeddings/)
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

logger = logging.getLogger(__name__)

# Cached local model (loaded once, reused for all embed_chunks calls)
_local_model = None


def _get_local_model():
    """Load and cache the local embedding model."""
    global _local_model
    if _local_model is None:
        from sentence_transformers import SentenceTransformer
        _local_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _local_model


# Embedding dimensions for each model
OPENAI_DIMENSION = 1536  # text-embedding-3-small
MINILM_DIMENSION = 384   # all-MiniLM-L6-v2

# OpenAI text-embedding-3-small max context: 8191 tokens
# Code has ~2 chars/token; use 14k chars (~7k tokens) to stay under limit
OPENAI_MAX_CHARS = 14_000


def embed_chunks(
    chunks: List[Dict[str, Any]],
    model: str = "openai",
    batch_size: int = 50,
    log_truncation: bool = False
) -> List[Dict[str, Any]]:
    """
    Embed chunks using the specified model and return them with embedding vectors.

    Accepts the full chunk list from the chunker, embeds in configurable batches,
    and adds an "embedding" field (list of floats) to each chunk dict.

    Args:
        chunks: List of chunk dicts from build_chunks_from_repo (must have "source")
        model: "openai" for text-embedding-3-small (API), "local" for all-MiniLM-L6-v2
        batch_size: Number of chunks to embed per API/local call (default 50)
        log_truncation: If True and model=="openai", log which chunks were truncated

    Returns:
        Same chunk list with "embedding" field added to each chunk

    Raises:
        ValueError: If model is not "openai" or "local"
    """
    if not chunks:
        return chunks

    if model not in ("openai", "local"):
        raise ValueError(f"model must be 'openai' or 'local', got {model!r}")

    # Prepare texts to embed (use source field)
    texts = [chunk.get("source", "") for chunk in chunks]

    # Truncate for OpenAI: max 8191 tokens; truncate to ~7k tokens
    truncated_info: List[tuple] = []  # (chunk_id, name, original_len)
    if model == "openai":
        new_texts = []
        for i, t in enumerate(texts):
            if len(t) > OPENAI_MAX_CHARS:
                truncated_info.append((
                    chunks[i].get("id", "?"),
                    chunks[i].get("name", "?"),
                    len(t)
                ))
            new_texts.append(_truncate_for_openai(t))
        texts = new_texts

    # Load local model once (cached at module level)
    local_model = _get_local_model() if model == "local" else None

    # Process in batches
    all_embeddings: List[List[float]] = []
    num_batches = (len(texts) + batch_size - 1) // batch_size

    for batch_idx in range(num_batches):
        start = batch_idx * batch_size
        end = min(start + batch_size, len(texts))
        batch_texts = texts[start:end]

        try:
            if model == "openai":
                embeddings = _embed_batch_openai(batch_texts)
            else:
                embeddings = _embed_batch_local(batch_texts, local_model)

            all_embeddings.extend(embeddings)
            logger.info(
                "Embedded batch %d/%d (%d chunks)",
                batch_idx + 1,
                num_batches,
                len(batch_texts)
            )
        except Exception as e:
            logger.warning(
                "Skipping batch %d/%d due to error: %s",
                batch_idx + 1,
                num_batches,
                e
            )
            # Append zero vectors so chunk count stays aligned (caller can filter)
            dim = OPENAI_DIMENSION if model == "openai" else MINILM_DIMENSION
            all_embeddings.extend([[0.0] * dim for _ in batch_texts])

    # Attach embeddings to chunks
    for chunk, embedding in zip(chunks, all_embeddings):
        chunk["embedding"] = embedding

    # Log truncation when requested (OpenAI model)
    if log_truncation and truncated_info:
        print("\n" + "=" * 70)
        print("TRUNCATION DIAGNOSIS (OpenAI model)")
        print("=" * 70)
        print(f"Chunks truncated: {len(truncated_info)} / {len(chunks)}")
        print(f"Limit: {OPENAI_MAX_CHARS:,} chars")
        print()
        for chunk_id, name, orig_len in truncated_info:
            print(f"  {chunk_id}")
            print(f"    name: {name}, original length: {orig_len:,} chars")
        print("=" * 70 + "\n")

    return chunks


def _truncate_for_openai(text: str) -> str:
    """Truncate text to ~6.6k tokens (20k chars) to stay under OpenAI 8191 limit."""
    if len(text) <= OPENAI_MAX_CHARS:
        return text
    return text[:OPENAI_MAX_CHARS]


def _embed_batch_openai(texts: List[str]) -> List[List[float]]:
    """Embed a batch using OpenAI text-embedding-3-small."""
    import os
    from openai import OpenAI

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set in environment (check .env)")

    client = OpenAI(api_key=api_key)
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=texts
    )
    # Response is ordered by input order
    by_idx = {item.index: item.embedding for item in response.data}
    return [by_idx[i] for i in range(len(texts))]


def _embed_batch_local(texts: List[str], model: Any) -> List[List[float]]:
    """Embed a batch using sentence-transformers all-MiniLM-L6-v2."""
    embeddings = model.encode(texts, convert_to_numpy=True)
    return [e.tolist() for e in embeddings]
