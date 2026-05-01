"""Backwards-compat shim. Use ``agents.prompts.library`` directly for new code.

This module exists so older imports keep working:
    from agents.prompts import system_prompts
    system_prompts.writer_prompt(...)
    system_prompts.PLATFORM_RULES
"""

from __future__ import annotations

from typing import Any

from .library import (
    HOOK_STRATEGIES,
    PLATFORM_RULES,
    Platform,
    detect_generic_phrases,
    generation_prompt,
    generation_user_prompt,
    hook_for_index,
)

__all__ = [
    "PLATFORM_RULES",
    "HOOK_STRATEGIES",
    "Platform",
    "detect_generic_phrases",
    "writer_prompt",
    "writer_user_prompt",
    "hook_for_index",
]


def writer_prompt(
    *,
    platform: Platform,
    kb_context: str = "",
    references: list[dict[str, Any]] | None = None,
    style_rules: list[dict[str, Any]] | None = None,
    variant_label: str = "A",
) -> str:
    """Legacy single-string return. New code should call generation_prompt
    which returns (system, hook_name) — the hook name is useful for UI."""
    index = ord(variant_label.upper()[0]) - ord("A") if variant_label else 0
    system, _hook = generation_prompt(
        platform=platform,
        variant_index=index,
        kb_context=kb_context,
        references=references,
        style_rules=style_rules,
    )
    return system


writer_user_prompt = generation_user_prompt
