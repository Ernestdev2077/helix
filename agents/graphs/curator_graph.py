"""Curator graph — extracts declarative StyleRules from references + winners.

Run on demand (or nightly). Input: workspace_id, brand_id. Process:
    1. Load all references for this brand
    2. Load all starred PostVariants (proxies for A/B winners in MVP without real metrics)
    3. Ask the LLM to extract 1-3 patterns with evidence
    4. POST proposed StyleRules to Django

Output: list of `proposed_rules` with confidence + evidence_reference_ids.
"""

from __future__ import annotations

import itertools
import json
import logging
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from ..event_bus import get_bus
from ..tools.db import (
    fetch_all_references_for_brand,
    fetch_brand,
    fetch_starred_variants,
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
    proposed_rules: list[dict[str, Any]]


async def _emit(run_id: str, **kwargs: Any) -> None:
    counter = _CURATOR_SEQ.setdefault(run_id, itertools.count(1))
    bus = await get_bus()
    await bus.publish(run_id=run_id, sequence=next(counter), **kwargs)


async def load_node(state: CuratorState) -> dict[str, Any]:
    run_id = state["run_id"]
    workspace_id = state["workspace_id"]
    brand_id = state["brand_id"]

    await _emit(run_id, kind="node_started", node_name="curator_load",
                message="Loading references and winning variants...")

    brand = await fetch_brand(brand_id) or {}
    references = await fetch_all_references_for_brand(
        workspace_id=workspace_id, brand_id=brand_id, limit=30
    )
    winners = await fetch_starred_variants(
        workspace_id=workspace_id, brand_id=brand_id, limit=20
    )

    await _emit(
        run_id, kind="node_finished", node_name="curator_load",
        message=f"Loaded {len(references)} refs + {len(winners)} winners",
    )
    return {"brand": brand, "references": references, "winners": winners}


def _build_extract_prompt(state: CuratorState) -> tuple[str, str]:
    brand = state.get("brand") or {}
    refs = state.get("references", [])
    winners = state.get("winners", [])

    refs_block = "\n\n".join(
        f"REF[{i+1}] (id={r['id']}, platform={r['platform']}, likes={r.get('likes_count', 0)}):\n{r['raw_text'][:500]}"
        for i, r in enumerate(refs[:15])
    ) or "(no references yet)"

    winners_block = "\n\n".join(
        f"WIN[{i+1}] (variant_id={w['id']}, platform={w['platform']}):\n{w['content'][:500]}"
        for i, w in enumerate(winners[:10])
    ) or "(no winners yet)"

    system = """You are a content strategist analyzing what makes social media posts successful for one brand.

Your task: extract 1 to 3 short, ACTIONABLE style rules from the references and winners below.

Each rule must:
- Be 5-15 words, imperative ("Open with a concrete number", "Avoid corporate buzzwords")
- Be DIFFERENT from already-known generic best practices — find brand-specific or platform-specific patterns
- Be supported by AT LEAST 2 examples (refs or winners)
- Have a confidence score 0.0-1.0 (raise it the more evidence supports it)

Output STRICT JSON:
{
  "rules": [
    {
      "rule_text": "string, 5-15 words, imperative",
      "rationale": "1-2 sentences: which specific examples support this",
      "scope": "global" | "platform",
      "platform": "" | "x" | "reddit" | "linkedin",
      "confidence": 0.0-1.0,
      "evidence_reference_ids": ["uuid", ...]
    }
  ]
}

If there are not enough examples to extract any meaningful rule yet, return {"rules": []}."""

    user = f"""BRAND: {brand.get('name', '?')}
DESCRIPTION: {brand.get('description', '')}
EXISTING VOICE DO: {brand.get('voice_do') or []}
EXISTING VOICE DON'T: {brand.get('voice_dont') or []}

LIKED REFERENCES (the team explicitly liked these):
{refs_block}

WINNING VARIANTS (the team starred these as best A/B picks):
{winners_block}

Now extract style rules as JSON."""
    return system, user


def _parse_json_loose(text: str) -> dict[str, Any]:
    """LLMs sometimes wrap JSON in fences or add prose. Try to extract."""
    text = text.strip()
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
    return {"rules": []}


async def extract_node(state: CuratorState) -> dict[str, Any]:
    run_id = state["run_id"]
    refs = state.get("references", [])
    winners = state.get("winners", [])

    if len(refs) + len(winners) < 2:
        await _emit(
            run_id, kind="node_finished", node_name="curator_extract",
            message="Not enough data yet — need at least 2 examples",
        )
        return {"proposed_rules": []}

    await _emit(run_id, kind="node_started", node_name="curator_extract",
                message="Extracting style patterns...")

    system, user = _build_extract_prompt(state)
    response = await chat_complete(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        role="curator",
        temperature=0.2,
        max_tokens=1500,
    )
    parsed = _parse_json_loose(response["content"])
    raw_rules = parsed.get("rules", [])

    valid_ref_ids = {r["id"] for r in refs}
    cleaned: list[dict[str, Any]] = []
    for r in raw_rules[:5]:
        if not isinstance(r, dict) or not r.get("rule_text"):
            continue
        evidence_ids = [eid for eid in r.get("evidence_reference_ids", []) if eid in valid_ref_ids]
        cleaned.append({
            "rule_text": str(r["rule_text"])[:400],
            "rationale": str(r.get("rationale", ""))[:1000],
            "scope": r.get("scope", "global"),
            "platform": r.get("platform", "") if r.get("scope") == "platform" else "",
            "confidence": float(r.get("confidence", 0.5)),
            "evidence_reference_ids": evidence_ids,
        })

    await _emit(
        run_id, kind="node_finished", node_name="curator_extract",
        message=f"Proposed {len(cleaned)} rule(s)",
        data={"rules_preview": [r["rule_text"] for r in cleaned]},
        tokens_in=response.get("tokens_in", 0),
        tokens_out=response.get("tokens_out", 0),
    )
    return {"proposed_rules": cleaned}


async def persist_node(state: CuratorState) -> dict[str, Any]:
    run_id = state["run_id"]
    rules = state.get("proposed_rules", [])

    if rules:
        await report_curation_completed({
            "run_id": run_id,
            "workspace_id": state["workspace_id"],
            "brand_id": state["brand_id"],
            "proposed_rules": rules,
        })
        await _emit(
            run_id, kind="info", node_name="curator_persist",
            message=f"Persisted {len(rules)} proposed rule(s)",
        )
    else:
        await _emit(
            run_id, kind="info", node_name="curator_persist",
            message="No rules to persist",
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
