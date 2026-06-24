"""
Mike RAG Service
────────────────
Thin FastAPI wrapper around Qdrant + sentence-transformers that exposes:
  POST /ingest           — embed a document chunk and upsert into Qdrant
  POST /ingest/batch     — batch ingest multiple chunks
  POST /search           — semantic search, returns ranked passages
  DELETE /document/{id}  — remove a document from the index
  GET  /health           — liveness probe
"""

from __future__ import annotations

import logging
import os
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from sentence_transformers import SentenceTransformer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY") or None
COLLECTION = os.getenv("QDRANT_COLLECTION", "mike_docs")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
TOP_K_DEFAULT = int(os.getenv("RAG_TOP_K", "5"))

app = FastAPI(title="Mike RAG Service", version="1.0.0")

_model: SentenceTransformer | None = None
_qdrant: QdrantClient | None = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        logger.info("Loading embedding model: %s", EMBEDDING_MODEL)
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def get_qdrant() -> QdrantClient:
    global _qdrant
    if _qdrant is None:
        _qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    return _qdrant


def ensure_collection() -> None:
    client = get_qdrant()
    dim = get_model().get_sentence_embedding_dimension()
    existing = {c.name for c in client.get_collections().collections}
    if COLLECTION not in existing:
        logger.info("Creating Qdrant collection '%s' (dim=%d)", COLLECTION, dim)
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )


def _doc_point_id(document_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, document_id))


# ── Models ────────────────────────────────────────────────────────────────────

class IngestRequest(BaseModel):
    document_id: str
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchRequest(BaseModel):
    query: str
    top_k: int = TOP_K_DEFAULT
    score_threshold: float | None = None


class SearchResult(BaseModel):
    document_id: str
    text: str
    score: float
    metadata: dict[str, Any]


# ── Lifecycle ─────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup() -> None:
    try:
        ensure_collection()
        logger.info("RAG service ready (collection=%s)", COLLECTION)
    except Exception as exc:  # pragma: no cover
        logger.warning("Could not initialise collection at startup: %s", exc)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "collection": COLLECTION, "model": EMBEDDING_MODEL}


@app.post("/ingest")
def ingest(req: IngestRequest):
    ensure_collection()
    embedding = get_model().encode(req.text).tolist()
    point_id = _doc_point_id(req.document_id)
    get_qdrant().upsert(
        collection_name=COLLECTION,
        points=[
            PointStruct(
                id=point_id,
                vector=embedding,
                payload={"document_id": req.document_id, "text": req.text, **req.metadata},
            )
        ],
    )
    return {"status": "ingested", "point_id": point_id}


@app.post("/ingest/batch")
def ingest_batch(docs: list[IngestRequest]):
    ensure_collection()
    model = get_model()
    texts = [d.text for d in docs]
    embeddings = model.encode(texts, show_progress_bar=False)
    points = [
        PointStruct(
            id=_doc_point_id(doc.document_id),
            vector=emb.tolist(),
            payload={"document_id": doc.document_id, "text": doc.text, **doc.metadata},
        )
        for doc, emb in zip(docs, embeddings)
    ]
    get_qdrant().upsert(collection_name=COLLECTION, points=points)
    return {"status": "ingested", "count": len(points)}


@app.post("/search", response_model=list[SearchResult])
def search(req: SearchRequest):
    ensure_collection()
    query_vec = get_model().encode(req.query).tolist()
    results = get_qdrant().search(
        collection_name=COLLECTION,
        query_vector=query_vec,
        limit=req.top_k,
        score_threshold=req.score_threshold,
    )
    return [
        SearchResult(
            document_id=r.payload.get("document_id", ""),
            text=r.payload.get("text", ""),
            score=r.score,
            metadata={k: v for k, v in r.payload.items() if k not in ("document_id", "text")},
        )
        for r in results
    ]


@app.delete("/document/{document_id}")
def delete_document(document_id: str):
    try:
        get_qdrant().delete(
            collection_name=COLLECTION,
            points_selector=[_doc_point_id(document_id)],
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"status": "deleted", "document_id": document_id}


@app.get("/stats")
def stats():
    try:
        info = get_qdrant().get_collection(COLLECTION)
        return {
            "collection": COLLECTION,
            "vectors_count": info.vectors_count,
            "points_count": info.points_count,
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
