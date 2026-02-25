"""
ChromaDB storage layer for semantic code search.

Takes embedded chunks from the embedder and stores them in a persistent ChromaDB
collection. Supports upsert for re-running the pipeline and query for retrieval.

Concepts:
- Collection: A named container of vectors + metadata. One collection per codebase
  or index (e.g. "flask_chunks"). Maps to our use case: one collection holds all
  code chunks for a repo.
- Per entry ChromaDB stores: (1) id - unique string, we use chunk id (filepath::name);
  (2) document - the source text; (3) metadata - name, type, file_path, etc.;
  (4) embedding - the vector. Metadata must be str/int/bool only.
- Upsert: Insert or update by id. Use instead of add so re-running the pipeline
  updates existing chunks rather than failing on duplicate ids.
- query(): Returns nearest neighbors. n_results controls how many to return.
  Result includes ids, documents, metadatas, distances (lower = more similar).
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)

# Persistent storage path: backend/vectordb/chroma_db/
_STORAGE_PATH = Path(__file__).resolve().parent / "chroma_db"
_BATCH_SIZE = 100


def get_collection_count(collection_name: str) -> int:
    """Return the number of items in the collection, or 0 if it does not exist."""
    try:
        client = _get_client()
        col = client.get_collection(name=collection_name)
        return col.count()
    except Exception:
        return 0


def delete_collections(*names: str) -> None:
    """Delete ChromaDB collections by name."""
    client = _get_client()
    for name in names:
        try:
            client.delete_collection(name)
            logger.info("Deleted collection '%s'", name)
        except Exception as e:
            logger.warning("Could not delete '%s': %s", name, e)


def _get_client() -> chromadb.PersistentClient:
    """Get or create persistent ChromaDB client."""
    _STORAGE_PATH.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(
        path=str(_STORAGE_PATH),
        settings=Settings(anonymized_telemetry=False),
    )


def store_chunks(
    chunks: List[Dict[str, Any]],
    collection_name: str,
    batch_size: int = 100,
) -> chromadb.Collection:
    """
    Store embedded chunks in a persistent ChromaDB collection.

    Creates or retrieves a collection by name, upserts chunks in batches.
    Uses chunk id as ChromaDB id, source as document, metadata fields as
    ChromaDB metadata, and embedding as the vector.

    Args:
        chunks: List of chunk dicts with id, source, embedding, and metadata
        collection_name: Name of the ChromaDB collection
        batch_size: Number of chunks per upsert batch (default 100)

    Returns:
        The ChromaDB collection
    """
    if not chunks:
        logger.warning("No chunks to store")
        client = _get_client()
        return client.get_or_create_collection(name=collection_name)

    client = _get_client()
    collection = client.get_or_create_collection(name=collection_name)

    num_batches = (len(chunks) + batch_size - 1) // batch_size

    for batch_idx in range(num_batches):
        start = batch_idx * batch_size
        end = min(start + batch_size, len(chunks))
        batch = chunks[start:end]

        ids = []
        embeddings = []
        documents = []
        metadatas = []

        for chunk in batch:
            chunk_id = chunk.get("id")
            if not chunk_id:
                logger.warning("Skipping chunk with missing id")
                continue
            ids.append(chunk_id)
            embeddings.append(chunk.get("embedding", []))
            documents.append(chunk.get("source", ""))

            # ChromaDB metadata: strings and ints only
            meta = {
                "name": str(chunk.get("name", "")),
                "type": str(chunk.get("type", "")),
                "file_path": str(chunk.get("file_path", "")),
                "start_line": int(chunk.get("start_line", 0)),
                "end_line": int(chunk.get("end_line", 0)),
                "parent_class": str(chunk.get("parent_class", "")),
            }
            metadatas.append(meta)

        try:
            collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )
            logger.info(
                "Stored batch %d/%d (%d chunks)",
                batch_idx + 1,
                num_batches,
                len(batch),
            )
        except Exception as e:
            logger.warning("Skipping batch %d/%d due to error: %s", batch_idx + 1, num_batches, e)

    return collection


def query_collection(
    query_embedding: List[float],
    collection_name: str,
    n_results: int = 5,
) -> List[Dict[str, Any]]:
    """
    Query the collection for nearest neighbors to the query embedding.

    Args:
        query_embedding: Vector embedding of the query (same dimension as stored)
        collection_name: Name of the ChromaDB collection
        n_results: Number of nearest neighbors to return (default 5)

    Returns:
        List of result dicts, each with metadata, source (document), and distance
    """
    client = _get_client()
    collection = client.get_collection(name=collection_name)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=["metadatas", "documents", "distances"],
    )

    # Single query: results are lists of lists, take first batch
    ids = results["ids"][0] if results["ids"] else []
    metadatas = results["metadatas"][0] if results["metadatas"] else []
    documents = results["documents"][0] if results["documents"] else []
    distances = results["distances"][0] if results.get("distances") else []

    output = []
    for i, chunk_id in enumerate(ids):
        meta = metadatas[i] if i < len(metadatas) else {}
        doc = documents[i] if i < len(documents) else ""
        dist = distances[i] if i < len(distances) else None

        output.append({
            "id": chunk_id,
            "metadata": meta,
            "source": doc,
            "distance": dist,
        })

    return output
