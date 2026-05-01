"""LLM call wrapper — routes through LiteLLM, primarily via OpenRouter.

Routing strategy:
- writer agents → cheap fast model (gpt-4o-mini via OpenRouter)
- critic agent  → quality reasoning (claude-3.5-sonnet)
- curator      → quality reasoning (claude-3.5-sonnet)

If no provider key is configured, falls back to stub content so the graph
can still run end-to-end in dev.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Literal

import httpx

log = logging.getLogger(__name__)

EMBEDDING_DIM = 1536

Platform = Literal["x", "reddit", "linkedin"]
Role = Literal["writer", "critic", "curator", "analyst"]


def _has_any_provider_key() -> bool:
    return bool(
        os.getenv("OPENROUTER_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("ANTHROPIC_API_KEY")
        or os.getenv("GROQ_API_KEY")
    )


def _model_for(role: Role) -> str:
    """Return the configured model for a given agent role.

    Defaults to OpenRouter-routed gpt-4o-mini for writers and claude for the
    rest. Override via env: HELIX_WRITER_MODEL, HELIX_CRITIC_MODEL, etc.
    """
    if role == "writer":
        return os.getenv("HELIX_WRITER_MODEL", "openrouter/openai/gpt-4o-mini")
    if role == "critic":
        return os.getenv("HELIX_CRITIC_MODEL", "openrouter/openai/gpt-4o-mini")
    if role == "curator":
        return os.getenv("HELIX_CURATOR_MODEL", "openrouter/openai/gpt-4o")
    return os.getenv("HELIX_DEFAULT_MODEL", "openrouter/openai/gpt-4o-mini")


def _stub_content(*, platform: Platform, messages: list[dict[str, Any]]) -> dict[str, Any]:
    user_msg = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
    snippets = {
        "x": f"[stub X post for: {user_msg[:60]}... — #SMM #AI]",
        "reddit": f"[stub Reddit post for: {user_msg[:100]}...]",
        "linkedin": f"[stub LinkedIn post for: {user_msg[:80]}...]",
    }
    return {
        "content": snippets.get(platform, f"[stub {platform} post]"),
        "tokens_in": 0,
        "tokens_out": 0,
        "stub": True,
    }


async def chat_complete(
    *,
    messages: list[dict[str, Any]],
    role: Role = "writer",
    platform: Platform = "x",
    model: str | None = None,
    temperature: float = 0.85,
    max_tokens: int = 1024,
) -> dict[str, Any]:
    use_model = model or _model_for(role)

    if not _has_any_provider_key():
        log.info("No LLM key configured — returning stub for %s/%s", role, platform)
        return _stub_content(platform=platform, messages=messages)

    try:
        import litellm

        kwargs: dict[str, Any] = {
            "model": use_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if use_model.startswith("openrouter/"):
            kwargs["extra_headers"] = {
                "HTTP-Referer": "https://github.com/Ernestdev2077/helix",
                "X-Title": "helix",
            }

        response = await litellm.acompletion(**kwargs)
        choice = response["choices"][0]
        usage = response.get("usage") or {}
        return {
            "content": choice["message"]["content"],
            "tokens_in": usage.get("prompt_tokens", 0),
            "tokens_out": usage.get("completion_tokens", 0),
            "model": use_model,
            "stub": False,
        }
    except Exception as exc:  # noqa: BLE001
        log.exception("LiteLLM call failed for %s, falling back to stub: %s", use_model, exc)
        return _stub_content(platform=platform, messages=messages)


# ---------------------------------------------------------------------------
# Embeddings — used by retriever for KB-chunk similarity search
# ---------------------------------------------------------------------------
async def embed(texts: list[str]) -> list[list[float]]:
    """Embed a batch of strings. Picks OpenRouter or OpenAI depending on which
    key is configured. Returns a list of EMBEDDING_DIM-vectors. Falls back to
    stub vectors if no key is set so the graph still runs."""
    if not texts:
        return []
    if os.getenv("OPENROUTER_API_KEY"):
        url = "https://openrouter.ai/api/v1/embeddings"
        headers = {
            "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/Ernestdev2077/helix",
            "X-Title": "helix",
        }
        model = "openai/text-embedding-3-small"
    elif os.getenv("OPENAI_API_KEY"):
        url = "https://api.openai.com/v1/embeddings"
        headers = {
            "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
            "Content-Type": "application/json",
        }
        model = "text-embedding-3-small"
    else:
        log.warning("No embedding key configured — returning stub vectors")
        return [_stub_vector(t) for t in texts]

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(url, headers=headers, json={"model": model, "input": texts})
            r.raise_for_status()
            data = r.json()
        return [item["embedding"] for item in data.get("data", [])]
    except Exception as exc:  # noqa: BLE001
        log.exception("embed() failed, returning stubs: %s", exc)
        return [_stub_vector(t) for t in texts]


def _stub_vector(text: str) -> list[float]:
    import hashlib

    h = hashlib.sha256(text.encode()).digest()
    return [(h[i % len(h)] - 128) / 128.0 for i in range(EMBEDDING_DIM)]
