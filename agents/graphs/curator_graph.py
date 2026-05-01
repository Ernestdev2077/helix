"""Curator graph — extracts winning patterns + style rules from real outcomes.

Now operates in two modes side-by-side:

  - Learning mode: when there are A/B winner-vs-siblings cases, ask the LLM
    to compare and explain WHY one variant won. Output goes into both
    WinningPattern (quantified) and StyleRule (declarative, requires user
    approval).

  - Reference mode (fallback): when there are not enough A/B cases yet,
    extract patterns from liked References alone (the previous behavior).

Both modes return the same JSON shape so the Django callback handles them
uniformly. The user always sees proposed StyleRules in Library.
"""

from __future__ import annotations

import itertools
import json
import logging
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from ..event_bus import get_bus
from ..prompts import library
from ..tools.db import (
    fetch_all_references_for_brand,
    fetch_brand,
    fetch_brand_dna,
    fetch_starred_variants,
    fetch_winner_cases,
)
from ..tools.django_api import report_curation_completed
from ..tools.llm import chat_complete

log = logging.getLogger(__name__)

_CURATOR_SEQ: dict[str, itertools.count] = {}


class CuratorState(TypedDict, total=False):
    run_id: str
    workspace_id: str
    brand_id: str

    brand: dict[str, Any]
    references: list[dict[str, Any]]
    winners: list[dict[str, Any]]
    winner_cases: list[dict[str, Any]]
    aggregated_dna: dict[str, Any]

    proposed_rules: list[dict[str, Any]]
    winning_patterns: list[dict[str, Any]]


async def _emit(run_id: str, **kwargs: Any) -> None:
    counter = _CURATOR_SEQ.setdefault(run_id, itertools.count(1))
    bus = await get_bus()
    await bus.publish(run_id=run_id, sequence=next(counter), **kwargs)


# ---------------------------------------------------------------------------
# Load — refs + winners + winner-vs-siblings cases + DNA aggregate
# ---------------------------------------------------------------------------
async def load_node(state: CuratorState) -> dict[str, Any]:
    run_id = state["run_id"]
    workspace_id = state["workspace_id"]
    brand_id = state["brand_id"]

    await _emit(run_id, kind="node_started", node_name="curator_load",
                message="Loading references, winners, A/B cases, DNA...")

    brand = await fetch_brand(brand_id) or {}
    references = await fetch_all_references_for_brand(
        workspace_id=workspace_id, brand_id=brand_id, limit=30
    )
    winners = await fetch_starred_variants(
        workspace_id=workspace_id, brand_id=brand_id, limit=20
    )
    cases = await fetch_winner_cases(
        workspace_id=workspace_id, brand_id=brand_id, limit=5
    )
    dna = await fetch_brand_dna(workspace_id=workspace_id, brand_id=brand_id)

    await _emit(
        run_id,
        kind="node_finished",
        node_name="curator_load",
        message=(
            f"{len(references)} refs, {len(winners)} winners, "
            f"{len(cases)} A/B cases, DNA from {dna.get('source_count', 0)} refs"
        ),
    )
    return {
        "brand": brand,
        "references": references,
        "winners": winners,
        "winner_cases": cases,
        "aggregated_dna": dna,
    }


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


# ---------------------------------------------------------------------------
# Extract — single LLM call covering both learning + reference modes
# ---------------------------------------------------------------------------
async def extract_node(state: CuratorState) -> dict[str, Any]:
    run_id = state["run_id"]
    refs = state.get("references", [])
    cases = state.get("winner_cases", [])
    brand = state.get("brand", {})

    if len(refs) + len(cases) < 1:
        await _emit(
            run_id, kind="node_finished", node_name="curator_extract",
            message="Not enough data yet (need ≥1 reference or A/B case)",
        )
        return {"proposed_rules": [], "winning_patterns": []}

    await _emit(run_id, kind="node_started", node_name="curator_extract",
                message=f"Analyzing {len(cases)} A/B cases + {len(refs)} refs...")

    response = await chat_complete(
        messages=[
            {"role": "system", "content": library.learning_prompt()},
            {"role": "user", "content": library.learning_user(
                brand=brand,
                winner_cases=cases,
                references=refs,
            )},
        ],
        role="curator",
        temperature=0.2,
        max_tokens=2000,
    )
    parsed = _parse_json_loose(response.get("content", ""))

    valid_ref_ids = {r["id"] for r in refs}
    valid_winner_ids = set()
    for c in cases:
        if c.get("winner"):
            valid_winner_ids.add(c["winner"]["id"])

    cleaned_rules: list[dict[str, Any]] = []
    for r in (parsed.get("proposed_rules") or [])[:5]:
        if not isinstance(r, dict) or not r.get("rule_text"):
            continue
        evidence_ids = [eid for eid in r.get("evidence_reference_ids", []) if eid in valid_ref_ids]
        cleaned_rules.append({
            "rule_text": str(r["rule_text"])[:400],
            "rationale": str(r.get("rationale", ""))[:1000],
            "scope": r.get("scope", "global"),
            "platform": r.get("platform", "") if r.get("scope") == "platform" else "",
            "confidence": float(r.get("confidence", 0.5)),
            "evidence_reference_ids": evidence_ids,
        })

    cleaned_patterns: list[dict[str, Any]] = []
    for p in (parsed.get("winning_patterns") or [])[:5]:
        if not isinstance(p, dict) or not p.get("pattern_text"):
            continue
        evidence_ids = [vid for vid in p.get("evidence_winner_ids", []) if vid in valid_winner_ids]
        try:
            lift = float(p.get("lift", 0.2))
        except (ValueError, TypeError):
            lift = 0.2
        try:
            sample_size = int(p.get("sample_size", len(cases)))
        except (ValueError, TypeError):
            sample_size = len(cases)
        cleaned_patterns.append({
            "pattern_text": str(p["pattern_text"])[:400],
            "platform": p.get("platform", ""),
            "metric": str(p.get("metric", "engagement_rate"))[:40],
            "lift": lift,
            "sample_size": sample_size,
            "evidence_variant_ids": evidence_ids,
        })

    await _emit(
        run_id, kind="node_finished", node_name="curator_extract",
        message=f"Extracted {len(cleaned_rules)} rule(s) + {len(cleaned_patterns)} pattern(s)",
        data={
            "rules_preview": [r["rule_text"] for r in cleaned_rules],
            "patterns_preview": [p["pattern_text"] for p in cleaned_patterns],
        },
        tokens_in=response.get("tokens_in", 0),
        tokens_out=response.get("tokens_out", 0),
    )
    return {"proposed_rules": cleaned_rules, "winning_patterns": cleaned_patterns}


# ---------------------------------------------------------------------------
# Persist — single Django callback, both rules and patterns
# ---------------------------------------------------------------------------
async def persist_node(state: CuratorState) -> dict[str, Any]:
    run_id = state["run_id"]
    rules = state.get("proposed_rules", [])
    patterns = state.get("winning_patterns", [])

    if rules or patterns:
        await report_curation_completed({
            "run_id": run_id,
            "workspace_id": state["workspace_id"],
            "brand_id": state["brand_id"],
            "proposed_rules": rules,
            "winning_patterns": patterns,
            "aggregated_dna": state.get("aggregated_dna") or {},
        })
        await _emit(
            run_id, kind="info", node_name="curator_persist",
            message=f"Persisted {len(rules)} rule(s) + {len(patterns)} pattern(s)",
        )
    else:
        await _emit(
            run_id, kind="info", node_name="curator_persist",
            message="Nothing to persist",
        )
    return {}


def build_curator_graph():
    g = StateGraph(CuratorState)
    g.add_node("load", load_node)
    g.add_node("extract", extract_node)
    g.add_node("persist", persist_node)
    g.add_edge(START, "load")
    g.add_edge("load", "extract")
    g.add_edge("extract", "persist")
    g.add_edge("persist", END)
    return g.compile()


async def run_curator_graph(initial_state: CuratorState) -> CuratorState:
    graph = build_curator_graph()
    run_id = initial_state["run_id"]
    await _emit(run_id, kind="info", message="Curator graph started")
    try:
        result: CuratorState = await graph.ainvoke(initial_state)
        await _emit(run_id, kind="info", message="Curator graph finished")
        return result
    finally:
        _CURATOR_SEQ.pop(run_id, None)


__all__ = ["build_curator_graph", "run_curator_graph"]
