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

log = logging.getLogger(__name__)

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
