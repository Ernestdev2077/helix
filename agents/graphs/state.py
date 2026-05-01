"""Typed state for content / ab-variation / curator / dna graphs."""

from __future__ import annotations

import operator
from typing import Annotated, Any, Literal, TypedDict

Platform = Literal["x", "reddit", "linkedin"]


class VariantDraft(TypedDict, total=False):
    platform: Platform
    label: str  # "A", "B", "C", "D", "E", "F"
    content: str
    critic_notes: list[dict[str, Any]]
    hook_strategy: str
    inspired_by_reference_ids: list[str]
    inspired_by_rule_ids: list[str]


class ContentState(TypedDict, total=False):
    """State passed between nodes in the content graph."""

    run_id: str
    workspace_id: str
    brand_id: str
    post_id: str

    brief: str
    goals: list[str]
    tone_hints: list[str]
    target_platforms: list[Platform]
    pinned_reference_ids: list[str]

    # Populated by researcher
    kb_context: str
    brand_dna: dict[str, Any]

    # Populated by retriever
    retrieved_references: list[dict[str, Any]]
    active_style_rules: list[dict[str, Any]]
    winning_patterns: list[dict[str, Any]]
    use_evolution_framing: bool

    # Populated by writer(s) — fan-out merge via operator.add
    variants: Annotated[list[VariantDraft], operator.add]

    # Populated by critic
    critic_pass: bool
    critic_notes: list[dict[str, Any]]

    # Final output
    output: dict[str, Any]


class ABVariationState(TypedDict, total=False):
    """State for the A/B variation graph (refine a winning post)."""

    run_id: str
    workspace_id: str
    brand_id: str
    post_id: str
    source_variant_id: str
    source_content: str
    source_platform: Platform

    kb_context: str
    active_style_rules: list[dict[str, Any]]

    starting_label_index: int  # so generated D/E/F doesn't collide with A/B/C

    variants: Annotated[list[VariantDraft], operator.add]
    output: dict[str, Any]


class ReferenceDNAState(TypedDict, total=False):
    """State for the reference-DNA extraction graph."""

    run_id: str
    workspace_id: str
    brand_id: str
    reference_id: str
    reference_text: str
    reference_platform: str

    extracted: dict[str, Any]
    output: dict[str, Any]
