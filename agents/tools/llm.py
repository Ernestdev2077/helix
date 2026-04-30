"""LLM call wrapper — routes through LiteLLM for multi-provider support.

Currently returns stub content if no API key is configured, so the graph
can run end-to-end in dev without spending money.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Literal

from ..config import get_settings

log = logging.getLogger(__name__)

Platform = Literal["x", "reddit", "linkedin"]


def _has_any_provider_key() -> bool:
    return bool(
        os.getenv("OPENAI_API_KEY")
        or os.getenv("ANTHROPIC_API_KEY")
        or os.getenv("GROQ_API_KEY")
        or os.getenv("OPENROUTER_API_KEY")
    )


def _stub_content(*, platform: Platform, messages: list[dict[str, Any]]) -> dict[str, Any]:
    user_msg = next(
        (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
    )
    snippets = {
        "x": f"[stub X post based on: {user_msg[:60]}... — #SMM #AI]",
        "reddit": f"[stub Reddit post based on: {user_msg[:100]}...]",
        "linkedin": f"[stub LinkedIn post based on: {user_msg[:80]}...]",
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
    platform: Platform = "x",
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> dict[str, Any]:
    settings = get_settings()
    use_model = model or settings.default_model

    if not _has_any_provider_key():
        log.info("No LLM API key configured — returning stub for %s", platform)
        await asyncio.sleep(0.2)
        return _stub_content(platform=platform, messages=messages)

    try:
        import litellm

        response = await litellm.acompletion(
            model=use_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
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
        log.exception("LiteLLM call failed, falling back to stub: %s", exc)
        return _stub_content(platform=platform, messages=messages)
