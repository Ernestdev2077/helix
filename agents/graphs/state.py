"""Typed state for content generation graph."""

from __future__ import annotations

import operator
from typing import Annotated, Any, Literal, TypedDict

Platform = Literal["x", "reddit", "linkedin"]


class VariantDraft(TypedDict):
    platform: Platform
    label: str  # "A" / "B" / "C"
    content: str
    critic_notes: list[dict[str, Any]]
    inspired_by_reference_ids: list[str]
    inspired_by_rule_ids: list[str]


class ContentState(TypedDict, total=False):
    """State passed between nodes in the content graph."""

    run_id: str
    workspace_id: str
    brand_id: str

    brief: str
    goals: list[str]
    tone_hints: list[str]
    target_platforms: list[Platform]
    pinned_reference_ids: list[str]

    # Populated by researcher / retriever
    kb_context: str
    retrieved_references: list[dict[str, Any]]
    active_style_rules: list[dict[str, Any]]

    # Populated by writer(s)
    variants: Annotated[list[VariantDraft], operator.add]

    # Populated by critic
    critic_pass: bool
    critic_notes: list[dict[str, Any]]

    # Final output
    output: dict[str, Any]
