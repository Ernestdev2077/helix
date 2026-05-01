"""Reference DNA extraction graph — analyze the writing style of one reference.

Single-node graph. Auto-triggered when a Reference is created. Result is
written back into ``Reference.extracted_features`` so writers can see it.
"""

from __future__ import annotations

import itertools
import json
import logging
from typing import Any

from langgraph.graph import END, START, StateGraph

from ..event_bus import get_bus
from ..prompts import library
from ..tools.django_api import post_internal
from ..tools.llm import chat_complete
from .state import ReferenceDNAState

log = logging.getLogger(__name__)

_SEQUENCE_COUNTERS: dict[str, itertools.count] = {}


def _next_seq(run_id: str) -> int:
    counter = _SEQUENCE_COUNTERS.setdefault(run_id, itertools.count(1))
    return next(counter)


async def _emit(run_id: str, **kwargs: Any) -> None:
    bus = await get_bus()
    await bus.publish(run_id=run_id, sequence=_next_seq(run_id), **kwargs)


def _parse_json_loose(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass
    return {}


async def extract_node(state: ReferenceDNAState) -> dict[str, Any]:
    run_id = state["run_id"]
    text = state.get("reference_text") or ""
    platform = state.get("reference_platform") or ""

    await _emit(run_id, kind="node_started", node_name="dna_extract",
                message=f"Extracting writing DNA from {len(text)} chars...")

    if not text.strip():
        await _emit(run_id, kind="error", node_name="dna_extract",
                    message="Empty reference text")
        return {"extracted": {}}

    response = await chat_complete(
        messages=[
            {"role": "system", "content": library.reference_dna_prompt()},
            {"role": "user", "content": library.reference_dna_user(
                reference_text=text, platform=platform,
            )},
        ],
        role="curator",
        temperature=0.2,
        max_tokens=600,
    )
    parsed = _parse_json_loose(response.get("content", ""))

    cleaned: dict[str, Any] = {}
    if isinstance(parsed, dict):
        for k in ("tone", "structure", "hook_patterns"):
            v = parsed.get(k)
            if isinstance(v, str):
                cleaned[k] = v[:300]
        srules = parsed.get("style_rules") or []
        if isinstance(srules, list):
            cleaned["style_rules"] = [str(r)[:200] for r in srules[:3] if r]
        kp = parsed.get("key_phrases") or []
        if isinstance(kp, list):
            cleaned["key_phrases"] = [str(p)[:60] for p in kp[:5] if p]

    await _emit(
        run_id, kind="node_finished", node_name="dna_extract",
        message=(
            f"DNA extracted: tone='{cleaned.get('tone', '?')[:40]}'"
            if cleaned else "Failed to parse DNA"
        ),
        data={"extracted_keys": list(cleaned.keys())},
        tokens_in=response.get("tokens_in", 0),
        tokens_out=response.get("tokens_out", 0),
    )
    return {"extracted": cleaned}


async def persist_node(state: ReferenceDNAState) -> dict[str, Any]:
    run_id = state["run_id"]
    extracted = state.get("extracted") or {}
    ref_id = state.get("reference_id", "")

    if extracted and ref_id:
        result = await post_internal(
            "/api/v1/agent-runs/internal/reference-dna-completed/",
            {
                "run_id": run_id,
                "reference_id": ref_id,
                "extracted_features": extracted,
            },
        )
        await _emit(
            run_id,
            kind="info",
            node_name="dna_persist",
            message=("Persisted DNA to reference" if result.get("ok") else f"Persist failed: {result}"),
        )
    return {"output": {"extracted": extracted}}


def build_reference_dna_graph():
    g = StateGraph(ReferenceDNAState)
    g.add_node("extract", extract_node)
    g.add_node("persist", persist_node)
    g.add_edge(START, "extract")
    g.add_edge("extract", "persist")
    g.add_edge("persist", END)
    return g.compile()


async def run_reference_dna_graph(initial_state: ReferenceDNAState) -> ReferenceDNAState:
    graph = build_reference_dna_graph()
    run_id = initial_state["run_id"]
    await _emit(run_id, kind="info", message="Reference DNA graph started")
    try:
        result: ReferenceDNAState = await graph.ainvoke(initial_state)
        await _emit(run_id, kind="info", message="Reference DNA graph finished")
        return result
    finally:
        _SEQUENCE_COUNTERS.pop(run_id, None)


__all__ = ["build_reference_dna_graph", "run_reference_dna_graph"]
