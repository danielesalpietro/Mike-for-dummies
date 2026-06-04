import os
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from mem0 import Memory

app = FastAPI(title="Mike Mem0 Service")

_memory: Optional[Memory] = None


def _patch_anthropic_llm():
    """Remove top_p from Anthropic API calls — Claude 4.x rejects temperature+top_p together."""
    try:
        from mem0.llms import anthropic as _ant_mod
        AnthropicLLM = _ant_mod.AnthropicLLM
        _orig = AnthropicLLM.generate_response

        def _patched(self, messages, response_format=None, tools=None, tool_choice="auto"):
            # Claude 4.x: extract system messages to top-level param
            system_parts = [m["content"] for m in messages if m.get("role") == "system"]
            user_messages = [m for m in messages if m.get("role") != "system"]
            params = {
                "model": self.config.model,
                "messages": user_messages,
                "max_tokens": self.config.max_tokens,
            }
            if system_parts:
                params["system"] = "\n".join(system_parts)
            if self.config.temperature is not None:
                params["temperature"] = self.config.temperature
            # top_p intentionally omitted — Claude 4.x forbids temperature+top_p together
            if tools:
                params["tools"] = tools
                params["tool_choice"] = {"type": tool_choice}
            response = self.client.messages.create(**params)
            if tools:
                return response
            return response.content[0].text

        AnthropicLLM.generate_response = _patched
    except Exception:
        pass  # patch is best-effort


_patch_anthropic_llm()


def _build_embedder_config() -> dict:
    gemini_key = os.environ.get("GEMINI_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")

    if gemini_key:
        return {
            "provider": "gemini",
            "config": {
                "model": os.environ.get("MEM0_EMBEDDER_MODEL") or "gemini-embedding-001",
                "api_key": gemini_key,
            },
        }
    if openai_key:
        return {
            "provider": "openai",
            "config": {
                "model": os.environ.get("MEM0_EMBEDDER_MODEL") or "text-embedding-3-small",
                "api_key": openai_key,
            },
        }
    raise RuntimeError(
        "Mem0 richiede almeno GEMINI_API_KEY o OPENAI_API_KEY per gli embeddings."
    )


def get_memory() -> Memory:
    global _memory
    if _memory is None:
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        if not anthropic_key:
            raise RuntimeError("ANTHROPIC_API_KEY mancante.")

        config = {
            "vector_store": {
                "provider": "qdrant",
                "config": {
                    "collection_name": "mike_memories",
                    "host": os.environ["QDRANT_HOST"],
                    "port": int(os.environ.get("QDRANT_PORT", "6333")),
                    "embedding_model_dims": 768,
                },
            },
            "llm": {
                "provider": "anthropic",
                "config": {
                    "model": os.environ.get("MEM0_LLM_MODEL") or "claude-haiku-4-5-20251001",
                    "api_key": anthropic_key,
                    "max_tokens": 2000,
                },
            },
            "embedder": _build_embedder_config(),
            "version": "v1.1",
        }
        _memory = Memory.from_config(config_dict=config)
    return _memory


class AddRequest(BaseModel):
    messages: list[dict]
    user_id: str


class SearchRequest(BaseModel):
    query: str
    user_id: str
    limit: int = 5


@app.post("/memories/add")
def add_memories(req: AddRequest):
    try:
        result = get_memory().add(req.messages, user_id=req.user_id)
        return {"status": "ok", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/memories/search")
def search_memories(req: SearchRequest):
    try:
        results = get_memory().search(req.query, user_id=req.user_id, limit=req.limit)
        memories = [r["memory"] for r in (results.get("results") or results or [])]
        return {"memories": memories}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    return {"status": "ok"}
