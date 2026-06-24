"""
Mike Mem0 Service
──────────────────
Personalised memory layer for the platform.  Persists per-user facts and
preferences so the LLM "remembers" across sessions.

Routes:
  POST /memories/add               — add messages to a user's memory
  POST /memories/search            — semantic search over a user's memories
  GET  /memories/{user_id}         — list all memories for a user
  DELETE /memories/{user_id}       — wipe all memories for a user
  DELETE /memories/{user_id}/{id}  — delete one memory entry
  GET  /health
"""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql://mike:mike_secret@localhost:5432/mike")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY") or ""
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

app = FastAPI(title="Mike Mem0 Service", version="1.0.0")

_memory = None
_mem0_available = False

# Fallback in-process store used when mem0ai is misconfigured or unavailable.
_fallback: dict[str, list[dict]] = {}


def _init_mem0():
    global _memory, _mem0_available
    try:
        from mem0 import Memory

        config: dict[str, Any] = {
            "vector_store": {
                "provider": "qdrant",
                "config": {
                    "url": QDRANT_URL,
                    "api_key": QDRANT_API_KEY,
                    "collection_name": "mike_user_memories",
                },
            },
            "embedder": {
                "provider": "huggingface",
                "config": {"model": EMBEDDING_MODEL},
            },
        }
        _memory = Memory.from_config(config)
        _mem0_available = True
        logger.info("Mem0 initialised with Qdrant backend")
    except Exception as exc:
        logger.warning("Mem0 unavailable (%s) — using in-process fallback", exc)
        _mem0_available = False


_init_mem0()


# ── Models ────────────────────────────────────────────────────────────────────

class Message(BaseModel):
    role: str  # "user" | "assistant" | "system"
    content: str


class AddMemoryRequest(BaseModel):
    user_id: str
    messages: list[Message]
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchMemoryRequest(BaseModel):
    user_id: str
    query: str
    limit: int = 10


class MemoryEntry(BaseModel):
    id: str
    memory: str
    metadata: dict[str, Any] | None = None
    score: float | None = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fallback_add(user_id: str, messages: list[Message], metadata: dict) -> None:
    bucket = _fallback.setdefault(user_id, [])
    for msg in messages:
        if msg.role == "user":
            bucket.append(
                {
                    "id": f"fb_{len(bucket)}",
                    "memory": msg.content,
                    "metadata": metadata,
                }
            )


def _fallback_search(user_id: str, query: str, limit: int) -> list[MemoryEntry]:
    entries = _fallback.get(user_id, [])
    # Trivial substring match — good enough for the fallback path.
    scored = [e for e in entries if query.lower() in e["memory"].lower()]
    return [
        MemoryEntry(id=e["id"], memory=e["memory"], metadata=e.get("metadata"))
        for e in scored[-limit:]
    ]


def _mem0_to_entry(r: dict) -> MemoryEntry:
    return MemoryEntry(
        id=r.get("id", ""),
        memory=r.get("memory", ""),
        metadata=r.get("metadata"),
        score=r.get("score"),
    )


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "mem0_available": _mem0_available}


@app.post("/memories/add")
def add_memory(req: AddMemoryRequest):
    raw = [{"role": m.role, "content": m.content} for m in req.messages]
    if _mem0_available and _memory:
        result = _memory.add(raw, user_id=req.user_id, metadata=req.metadata)
        return {"status": "added", "result": result}
    _fallback_add(req.user_id, req.messages, req.metadata)
    return {"status": "added (fallback)"}


@app.post("/memories/search", response_model=list[MemoryEntry])
def search_memories(req: SearchMemoryRequest):
    if _mem0_available and _memory:
        results = _memory.search(req.query, user_id=req.user_id, limit=req.limit)
        return [_mem0_to_entry(r) for r in results]
    return _fallback_search(req.user_id, req.query, req.limit)


@app.get("/memories/{user_id}", response_model=list[MemoryEntry])
def get_all_memories(user_id: str):
    if _mem0_available and _memory:
        return [_mem0_to_entry(r) for r in _memory.get_all(user_id=user_id)]
    return [
        MemoryEntry(id=e["id"], memory=e["memory"], metadata=e.get("metadata"))
        for e in _fallback.get(user_id, [])
    ]


@app.delete("/memories/{user_id}")
def clear_user_memories(user_id: str):
    if _mem0_available and _memory:
        _memory.delete_all(user_id=user_id)
    else:
        _fallback.pop(user_id, None)
    return {"status": "cleared", "user_id": user_id}


@app.delete("/memories/{user_id}/{memory_id}")
def delete_one_memory(user_id: str, memory_id: str):
    if _mem0_available and _memory:
        _memory.delete(memory_id=memory_id)
    else:
        bucket = _fallback.get(user_id, [])
        _fallback[user_id] = [e for e in bucket if e["id"] != memory_id]
    return {"status": "deleted", "memory_id": memory_id}
