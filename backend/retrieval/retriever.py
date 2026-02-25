"""
Retrieval layer for semantic code search.

Provides embed_query() for single-string embedding and search() for end-to-end
natural language search over stored chunks.
"""

from typing import List, Dict, Any

from embeddings.embedder import embed_chunks
from vectordb.store import query_collection


def embed_query(query: str, model: str = "local") -> List[float]:
    """
    Embed a single natural language query string into a vector.

    Reuses embed_chunks() from embedder.py by wrapping the query in a minimal
    chunk dict. No logic duplication — the same models (all-MiniLM-L6-v2 for
    "local", text-embedding-3-small for "openai") and batching behavior apply.
    For a single string, embed_chunks processes it as a batch of 1.

    Args:
        query: Natural language search query (e.g. "how does Flask handle routing")
        model: "local" for MiniLM (offline), "openai" for API

    Returns:
        Embedding vector as list of floats
    """
    chunks = [{"source": query}]
    embedded = embed_chunks(chunks, model=model, batch_size=50)
    return embedded[0]["embedding"]


def search(
    query: str,
    collection_name: str,
    model: str = "local",
    n_results: int = 5,
) -> List[Dict[str, Any]]:
    """
    Search the collection for chunks most similar to the query.

    Embeds the query, queries the collection, and returns results sorted by
    distance ascending (most similar first).

    Args:
        query: Natural language search query
        collection_name: ChromaDB collection name
        model: "local" or "openai" (must match collection's embedding model)
        n_results: Number of results to return (default 5)

    Returns:
        List of result dicts with: name, type, file_path, start_line, end_line,
        parent_class, source, distance
    """
    embedding = embed_query(query, model=model)
    raw = query_collection(
        query_embedding=embedding,
        collection_name=collection_name,
        n_results=n_results,
    )

    # Flatten metadata into result and ensure sorted by distance
    results = []
    for r in raw:
        meta = r.get("metadata", {})
        results.append({
            "id": r.get("id", ""),
            "name": meta.get("name", ""),
            "type": meta.get("type", ""),
            "file_path": meta.get("file_path", ""),
            "start_line": meta.get("start_line", 0),
            "end_line": meta.get("end_line", 0),
            "parent_class": meta.get("parent_class", ""),
            "source": r.get("source", ""),
            "distance": r.get("distance"),
        })

    # Sort by distance ascending (most similar first)
    results.sort(key=lambda x: (x["distance"] is None, x["distance"] or float("inf")))

    return results
