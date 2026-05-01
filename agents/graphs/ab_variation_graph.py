"""A/B variation graph — refine a winning variant with N psych triggers.

Flow:
    START -> load -> refine_x_3 -> finalize -> END

Input: source variant (a starred winner). We load brand context + active
rules, then ask the LLM for N reframings — each with a different
psychological trigger (curiosity / controversy / specificity / emotional).

Output is persisted as new PostVariant rows on the SAME post, with labels
continuing after the existing max (e.g. existing A/B/C -> new D/E/F).
"""

from __future__ import annotations

import itertools
import logging
from typing import Any

from langgraph.graph import END, START, StateGraph

from ..event_bus import get_bus
from ..prompts import library
from ..tools.db import (
    fetch_active_rules,
    fetch_brand,
    fetch_max_variant_label,
    fetch_variant_for_refine,
)
from ..tools.django_api import report_content_completed
from ..tools.llm import chat_complete
from .state import ABVariationState, VariantDraft

log = logging.getLogger(__name__)

REFINEMENTS_COUNT = 3  # one per psych trigger
_SEQUENCE_COUNTERS: dict[str, itertools.count] = {}


def _next_seq(run_id: str) -> int:
    counter = _SEQUENCE_COUNTERS.setdefault(run_id, itertools.count(1))
    return next(counter)


async def _emit(run_id: str, **kwargs: Any) -> None:
    bus = await get_bus()
    await bus.publish(run_id=run_id, sequence=_next_seq(run_id), **kwargs)


# ---------------------------------------------------------------------------
# Load — fetch source variant + brand + rules
# ---------------------------------------------------------------------------
async def load_node(state: ABVariationState) -> dict[str, Any]:
    run_id = state["run_id"]
    variant_id = state["source_variant_id"]
    await _emit(run_id, kind="node_started", node_name="ab_load",
                message="Loading source variant and brand context...")

    src = await fetch_variant_for_refine(variant_id=variant_id)
    if not src:
        await _emit(run_id, kind="error", node_name="ab_load",
                    message=f"Variant {variant_id} not found")
        return {"source_content": ""}

    brand_id = src["brand_id"]
    brand = await fetch_brand(brand_id) or {}
    rules = await fetch_active_rules(
        workspace_id=src["workspace_id"], brand_id=brand_id, platform=src["platform"]
    )

    # Find next available label letter so we don't collide
    max_label = await fetch_max_variant_label(post_id=src["post_id"])
    starting_index = (ord(max_label.upper()) - ord("A") + 1) if max_label else 0

    do_list = ", ".join(brand.get("voice_do") or []) or "(none)"
    dont_list = ", ".join(brand.get("voice_dont") or []) or "(none)"
    kb = (
        f"Brand: {brand.get('name', '?')}\n"
        f"Description: {brand.get('description') or '(none)'}\n"
        f"Voice DO: {do_list}\n"
        f"Voice DON'T: {dont_list}"
    ) if brand else ""

    await _emit(
        run_id, kind="node_finished", node_name="ab_load",
        message=f"Loaded variant {src['label']} ({src['platform']}, {len(src['content'])} chars)",
    )
    return {
        "post_id": src["post_id"],
        "workspace_id": src["workspace_id"],
        "brand_id": brand_id,
        "source_content": src["content"],
        "source_platform": src["platform"],
        "kb_context": kb,
        "active_style_rules": rules,
        "starting_label_index": starting_index,
    }


# ---------------------------------------------------------------------------
# Refine — produce REFINEMENTS_COUNT variants with different triggers
# ---------------------------------------------------------------------------
async def refine_node(state: ABVariationState) -> dict[str, Any]:
    run_id = state["run_id"]
    if not state.get("source_content"):
        return {"variants": []}

    platform = state["source_platform"]
    starting = state.get("starting_label_index", 0)
    labels = ["A", "B", "C", "D", "E", "F", "G", "H"]

    await _emit(
        run_id,
        kind="node_started",
        node_name="ab_refine",
        message=f"Reframing with {REFINEMENTS_COUNT} psych triggers...",
    )

    out: list[VariantDraft] = []
    total_in = total_out = 0
    for i in range(REFINEMENTS_COUNT):
        label = labels[(starting + i) % len(labels)]
        system, trigger_name = library.ab_variation_prompt(
            original_post=state["source_content"],
            platform=platform,
            trigger_index=i,
            kb_context=state.get("kb_context", ""),
            style_rules=state.get("active_style_rules", []),
        )
        user = library.ab_variation_user(
            original_post=state["source_content"],
            trigger_name=trigger_name,
        )
        try:
            response = await chat_complete(
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                role="writer",
                platform=platform,
                temperature=0.95 + i * 0.05,
            )
            content = response["content"]
            tokens_in = response.get("tokens_in", 0)
            tokens_out = response.get("tokens_out", 0)
            total_in += tokens_in
            total_out += tokens_out
        except Exception as exc:  # noqa: BLE001
            log.exception("AB refine failed for trigger %s", trigger_name)
            content = f"[refine error: {exc}]"
            tokens_in = tokens_out = 0

        variant: VariantDraft = {
            "platform": platform,
            "label": label,
            "content": content.strip(),
            "critic_notes": [],
            "hook_strategy": trigger_name,
            "inspired_by_reference_ids": [],
            "inspired_by_rule_ids": [
                r["id"] for r in state.get("active_style_rules", [])
            ],
        }
        out.append(variant)

        await _emit(
            run_id,
            kind="stream_chunk",
            node_name="ab_refine",
            message=f"{label} ({trigger_name}) ready — {len(content)} chars",
            data={
                "platform": platform,
                "label": label,
                "hook_strategy": trigger_name,
                "preview": content[:140],
            },
            tokens_in=tokens_in,
            tokens_out=tokens_out,
        )

    await _emit(
        run_id, kind="node_finished", node_name="ab_refine",
        message=f"Done — {len(out)} refined variants",
        tokens_in=total_in, tokens_out=total_out,
    )
    return {"variants": out}


# ---------------------------------------------------------------------------
# Finalize — persist via Django callback
# ---------------------------------------------------------------------------
async def finalize_node(state: ABVariationState) -> dict[str, Any]:
    run_id = state["run_id"]
    variants = state.get("variants", [])

    payload = {
        "run_id": run_id,
        "post_id": state.get("post_id", ""),
        "variants": variants,
        "critic_notes": [],
        "critic_pass": True,
        "append_only": True,  # signal to callback: append, don't replace
    }
    if state.get("post_id") and variants:
        result = await report_content_completed(payload)
        if result.get("ok"):
            await _emit(
                run_id, kind="info", node_name="ab_finalize",
                message=f"Persisted {result.get('variant_count', 0)} refined variants",
                data={"variant_count": result.get("variant_count", 0)},
            )
        else:
            await _emit(
                run_id, kind="error", node_name="ab_finalize",
                message=f"Persist failed: {result}",
            )

    await _emit(
        run_id, kind="node_finished", node_name="ab_finalize",
        message="A/B variation complete",
        data={"variant_count": len(variants)},
    )
    return {"output": payload}


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------
def build_ab_variation_graph():
    g = StateGraph(ABVariationState)
    g.add_node("load", load_node)
    g.add_node("refine", refine_node)
    g.add_node("finalize", finalize_node)
    g.add_edge(START, "load")
    g.add_edge("load", "refine")
    g.add_edge("refine", "finalize")
    g.add_edge("finalize", END)
    return g.compile()


async def run_ab_variation_graph(initial_state: ABVariationState) -> ABVariationState:
    graph = build_ab_variation_graph()
    run_id = initial_state["run_id"]
    await _emit(run_id, kind="info", message="A/B variation graph started",
                data={"source_variant_id": initial_state.get("source_variant_id")})
    try:
        result: ABVariationState = await graph.ainvoke(initial_state)
        await _emit(run_id, kind="info", message="A/B variation graph finished")
        return result
    finally:
        _SEQUENCE_COUNTERS.pop(run_id, None)


__all__ = ["build_ab_variation_graph", "run_ab_variation_graph"]
