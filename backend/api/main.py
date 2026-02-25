"""
FastAPI backend for semantic code search.

Endpoints: POST /search, GET /health
"""

import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware


# Load .env from backend/
_backend = Path(__file__).resolve().parent.parent
load_dotenv(_backend / ".env")  # try backend/.env
for p in [Path.cwd() / ".env", Path.cwd() / "backend" / ".env"]:
    if p.exists():
        load_dotenv(p)
        break

if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from retrieval.retriever import search
from vectordb.store import get_collection_count

# Config
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "flask_local")

# Request logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _warmup() -> None:
    """Initialize ChromaDB client and embedding model once at startup."""
    count = get_collection_count(COLLECTION_NAME)
    logger.info("Warmup: collection %s has %d chunks", COLLECTION_NAME, count)
    # Warm up embedding model (embedder caches at module level)
    search("warmup", collection_name=COLLECTION_NAME, model="local", n_results=1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: warm up ChromaDB and embedding model. Shutdown: no-op."""
    _warmup()
    yield


app = FastAPI(
    title="Semantic Code Search API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SearchRequest(BaseModel):
    query: str = Field(..., description="Natural language search query")
    n_results: int = Field(default=5, ge=1, le=50, description="Number of results")
    model: str = Field(default="local", description="Embedding model: local or openai")


class SearchResult(BaseModel):
    name: str
    type: str
    file_path: str
    start_line: int
    end_line: int
    parent_class: str
    source: str
    distance: float | None


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    model: str
    count: int


@app.post("/search", response_model=SearchResponse)
async def post_search(req: SearchRequest):
    """Search the codebase for chunks similar to the query."""
    query = (req.query or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="query cannot be empty")

    logger.info("POST /search query=%r n_results=%d model=%s", query, req.n_results, req.model)

    try:
        raw = search(
            query=query,
            collection_name=COLLECTION_NAME,
            model=req.model,
            n_results=req.n_results,
        )
    except Exception as e:
        logger.exception("Search failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

    results = [
        SearchResult(
            name=r.get("name", ""),
            type=r.get("type", ""),
            file_path=r.get("file_path", ""),
            start_line=r.get("start_line", 0),
            end_line=r.get("end_line", 0),
            parent_class=r.get("parent_class", ""),
            source=r.get("source", ""),
            distance=r.get("distance"),
        )
        for r in raw
    ]

    return SearchResponse(
        query=query,
        results=results,
        model=req.model,
        count=len(results),
    )


@app.get("/health")
async def get_health():
    """Health check: verify collection is populated."""
    chunk_count = get_collection_count(COLLECTION_NAME)
    return {
        "status": "ok",
        "collection": COLLECTION_NAME,
        "chunk_count": chunk_count,
    }
