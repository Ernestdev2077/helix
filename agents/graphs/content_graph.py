"""Content generation graph — LangGraph state machine.

Flow:
    START -> researcher -> retriever -> writer x N (per platform, fan-out)
          -> critic -> finalize -> END

Each platform-writer fans out to ``VARIANTS_PER_PLATFORM`` LLM calls in
sequence (sharing the same node, different hook strategies). Variants are
then collected by the framework via ``Annotated[list, operator.add]`` on
``state['variants']``.

Generation auto-switches to **evolution framing** (hard-constraint phrasing
of approved rules and winning patterns) as soon as the brand has both at
least one approved rule and at least one winning pattern. This is invisible
to the user except for an event in the timeline ("evolution mode active").

The critic node validates platform constraints (length) and scans for the
banned generic-AI phrases from the prompt library, attaching findings as
``critic_notes`` per variant.
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
    fetch_brand_dna,
    fetch_references,
    fetch_top_kb_chunks,
    fetch_winning_patterns,
)
from ..tools.django_api import report_content_completed
from ..tools.llm import chat_complete, embed
from .state import ContentState, Platform, VariantDraft

log = logging.getLogger(__name__)

VARIANTS_PER_PLATFORM = 3  # one per hook strategy: curiosity, controversy, story
_SEQUENCE_COUNTERS: dict[str, itertools.count] = {}


def _next_seq(run_id: str) -> int:
    counter = _SEQUENCE_COUNTERS.setdefault(run_id, itertools.count(1))
    return next(counter)


async def _emit(
    run_id: str,
    *,
    kind: str,
    node_name: str = "",
    message: str = "",
    data: dict[str, Any] | None = None,
    tokens_in: int = 0,
    tokens_out: int = 0,
    duration_ms: int = 0,
) -> None:
    bus = await get_bus()
    await bus.publish(
        run_id=run_id,
        sequence=_next_seq(run_id),
        kind=kind,
        node_name=node_name,
        message=message,
        data=data,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        duration_ms=duration_ms,
    )


# ---------------------------------------------------------------------------
# Researcher — load brand + voice + DNA aggregate
# ---------------------------------------------------------------------------
async def researcher_node(state: ContentState) -> dict[str, Any]:
    run_id = state["run_id"]
    brand_id = state.get("brand_id", "")
    workspace_id = state["workspace_id"]
    brief = state.get("brief", "")

    await _emit(run_id, kind="node_started", node_name="researcher",
                message="Loading brand voice, DNA, and relevant KB chunks...")

    brand = await fetch_brand(brand_id) if brand_id else None
    if not brand:
        await _emit(run_id, kind="node_finished", node_name="researcher",
                    message="No brand found — using defaults")
        return {"kb_context": "", "brand_dna": {}}

    do_list = ", ".join(brand.get("voice_do") or []) or "(none)"
    dont_list = ", ".join(brand.get("voice_dont") or []) or "(none)"
    kb_parts = [
        f"Brand: {brand['name']}",
        f"Description: {brand.get('description') or '(none)'}",
        f"Audience: {brand.get('target_audience') or '(general)'}",
        f"Voice description: {brand.get('voice_description') or '(default)'}",
        f"Voice DO: {do_list}",
        f"Voice DON'T: {dont_list}",
    ]

    # KB retrieval — embed brief, look up top-3 chunks across this brand's docs.
    kb_chunks: list[dict[str, Any]] = []
    if brief.strip():
        try:
            [query_vec] = await embed([brief[:1000]])
            kb_chunks = await fetch_top_kb_chunks(
                workspace_id=workspace_id, brand_id=brand_id,
                query_embedding=query_vec, k=3,
            )
        except Exception as exc:  # noqa: BLE001
            log.exception("KB retrieval failed: %s", exc)
            kb_chunks = []
    if kb_chunks:
        kb_parts.append("")
        kb_parts.append("BRAND KNOWLEDGE (top relevant chunks from your docs):")
        for c in kb_chunks:
            title = c.get("document_title") or "doc"
            kb_parts.append(f"--- from {title!r} ---")
            kb_parts.append(c.get("text", "")[:600])

    dna = await fetch_brand_dna(workspace_id=workspace_id, brand_id=brand_id)

    await _emit(
        run_id, kind="node_finished", node_name="researcher",
        message=(
            f"Loaded '{brand['name']}'"
            + (f" + {len(kb_chunks)} KB chunks" if kb_chunks else "")
            + (f" + DNA from {dna.get('source_count', 0)} refs" if dna else "")
        ),
        data={"kb_chunk_count": len(kb_chunks)},
    )
    return {"kb_context": "\n".join(kb_parts), "brand_dna": dna or {}}


# ---------------------------------------------------------------------------
# Retriever — top references + active style rules + winning patterns
# ---------------------------------------------------------------------------
async def retriever_node(state: ContentState) -> dict[str, Any]:
    run_id = state["run_id"]
    workspace_id = state["workspace_id"]
    brand_id = state.get("brand_id", "")
    platforms = state.get("target_platforms", [])

    await _emit(run_id, kind="node_started", node_name="retriever",
                message="Fetching references, rules, and winning patterns...")

    if not brand_id:
        await _emit(run_id, kind="node_finished", node_name="retriever",
                    message="No brand — skipping retrieval")
        return {"retrieved_references": [], "active_style_rules": [], "winning_patterns": []}

    refs: list[dict[str, Any]] = []
    rules: list[dict[str, Any]] = []
    patterns: list[dict[str, Any]] = []
    for p in platforms:
        refs += await fetch_references(
            workspace_id=workspace_id, brand_id=brand_id, platform=p, limit=3
        )
        rules += await fetch_active_rules(
            workspace_id=workspace_id, brand_id=brand_id, platform=p
        )
        patterns += await fetch_winning_patterns(
            workspace_id=workspace_id, brand_id=brand_id, platform=p
        )

    deduped_refs = _dedupe_by_id(refs)
    deduped_rules = _dedupe_by_id(rules)
    deduped_patterns = _dedupe_by_id(patterns)

    use_evolution = bool(deduped_rules) and bool(deduped_patterns)

    await _emit(
        run_id, kind="node_finished", node_name="retriever",
        message=(
            f"Loaded {len(deduped_refs)} refs, {len(deduped_rules)} rules, "
            f"{len(deduped_patterns)} winning patterns"
            + ("  [evolution mode]" if use_evolution else "")
        ),
        data={
            "ref_count": len(deduped_refs),
            "rule_count": len(deduped_rules),
            "pattern_count": len(deduped_patterns),
            "evolution_mode": use_evolution,
            "rules_preview": [r["rule_text"][:80] for r in deduped_rules[:3]],
        },
    )
    return {
        "retrieved_references": deduped_refs,
        "active_style_rules": deduped_rules,
        "winning_patterns": deduped_patterns,
        "use_evolution_framing": use_evolution,
    }


def _dedupe_by_id(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out = []
    for x in items:
        ident = x.get("id")
        if ident and ident not in seen:
            seen.add(ident)
            out.append(x)
    return out


# ---------------------------------------------------------------------------
# Writer — generates VARIANTS_PER_PLATFORM drafts for one platform
# ---------------------------------------------------------------------------
def _make_writer_node(platform: Platform):
    async def writer_node(state: ContentState) -> dict[str, Any]:
        run_id = state["run_id"]
        await _emit(
            run_id,
            kind="node_started",
            node_name=f"writer_{platform}",
            message=f"Drafting {VARIANTS_PER_PLATFORM} variants for {platform}...",
        )

        variants_out: list[VariantDraft] = []
        labels = ["A", "B", "C", "D", "E", "F"]
        total_in = total_out = 0

        for i in range(VARIANTS_PER_PLATFORM):
            label = labels[i]
            system, hook_name = library.generation_prompt(
                platform=platform,
                variant_index=i,
                kb_context=state.get("kb_context", ""),
                references=state.get("retrieved_references", []),
                style_rules=state.get("active_style_rules", []),
                winning_patterns=state.get("winning_patterns", []),
                brand_dna=state.get("brand_dna", {}),
                use_evolution_framing=state.get("use_evolution_framing", False),
            )
            user = library.generation_user_prompt(
                brief=state["brief"],
                goals=state.get("goals", []),
                tone_hints=state.get("tone_hints", []),
            )

            try:
                response = await chat_complete(
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    role="writer",
                    platform=platform,
                    temperature=0.85 + i * 0.1,
                )
                content = response["content"]
                tokens_in = response.get("tokens_in", 0)
                tokens_out = response.get("tokens_out", 0)
                total_in += tokens_in
                total_out += tokens_out
            except Exception as exc:  # noqa: BLE001
                log.exception("Writer failed for %s/%s", platform, label)
                content = f"[writer error: {exc}]"
                tokens_in = tokens_out = 0

            variant: VariantDraft = {
                "platform": platform,
                "label": label,
                "content": content.strip(),
                "critic_notes": [],
                "hook_strategy": hook_name,
                "inspired_by_reference_ids": [
                    r["id"] for r in state.get("retrieved_references", [])
                    if r.get("platform") in (platform, "")
                ],
                "inspired_by_rule_ids": [
                    r["id"] for r in state.get("active_style_rules", [])
                ],
            }
            variants_out.append(variant)

            await _emit(
                run_id,
                kind="stream_chunk",
                node_name=f"writer_{platform}",
                message=f"Variant {label} ({hook_name}) ready — {len(content)} chars",
                data={
                    "platform": platform,
                    "label": label,
                    "hook_strategy": hook_name,
                    "preview": content[:140],
                },
                tokens_in=tokens_in,
                tokens_out=tokens_out,
            )

        await _emit(
            run_id,
            kind="node_finished",
            node_name=f"writer_{platform}",
            message=f"Done — {len(variants_out)} variants",
            tokens_in=total_in,
            tokens_out=total_out,
        )
        return {"variants": variants_out}

    writer_node.__name__ = f"writer_{platform}"
    return writer_node


# ---------------------------------------------------------------------------
# Critic — platform constraints + anti-AI phrase scan
# ---------------------------------------------------------------------------
async def critic_node(state: ContentState) -> dict[str, Any]:
    run_id = state["run_id"]
    await _emit(run_id, kind="node_started", node_name="critic",
                message="Reviewing variants for length and AI tone...")

    notes: list[dict[str, Any]] = []
    for v in state.get("variants", []):
        issues: list[dict[str, Any]] = []
        length = len(v["content"])
        platform = v["platform"]

        if platform == "x" and length > 280:
            issues.append({
                "severity": "error",
                "message": f"X post exceeds 280 chars ({length})",
                "fix_suggestion": "Shorten or split into a numbered thread",
            })
        if platform == "linkedin" and length < 150:
            issues.append({
                "severity": "warn",
                "message": "LinkedIn posts under 150 chars tend to underperform",
                "fix_suggestion": "Add a concrete example or stat",
            })

        # Anti-AI phrase scan from the central library
        found = library.detect_generic_phrases(v["content"])
        if found:
            issues.append({
                "severity": "warn",
                "message": f"Generic AI phrases detected: {', '.join(found[:3])}"
                           + ("…" if len(found) > 3 else ""),
                "fix_suggestion": "Rewrite with concrete language; this kills authenticity",
            })

        v["critic_notes"] = issues
        notes.extend(
            [{"platform": platform, "label": v["label"], **i} for i in issues]
        )

    passed = all(n["severity"] != "error" for n in notes)
    await _emit(
        run_id, kind="node_finished", node_name="critic",
        message=f"{'Passed' if passed else 'Found errors'} ({len(notes)} notes)",
        data={"notes": notes, "passed": passed},
    )
    return {"critic_pass": passed, "critic_notes": notes}


# ---------------------------------------------------------------------------
# Finalize — persist back to Django
# ---------------------------------------------------------------------------
async def finalize_node(state: ContentState) -> dict[str, Any]:
    run_id = state["run_id"]
    variants = state.get("variants", [])

    callback_payload = {
        "run_id": run_id,
        "post_id": state.get("post_id", ""),
        "variants": variants,
        "critic_notes": state.get("critic_notes", []),
        "critic_pass": state.get("critic_pass", True),
    }
    if state.get("post_id"):
        result = await report_content_completed(callback_payload)
        if result.get("ok"):
            await _emit(
                run_id, kind="info", node_name="finalize",
                message=f"Persisted {result.get('variant_count', 0)} variants",
                data={"variant_count": result.get("variant_count", 0)},
            )
        else:
            await _emit(
                run_id, kind="error", node_name="finalize",
                message=f"Persist failed: {result}",
            )

    await _emit(
        run_id, kind="node_finished", node_name="finalize",
        message="Run complete",
        data={"variant_count": len(variants)},
    )
    return {"output": callback_payload}


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------
def build_content_graph():
    g = StateGraph(ContentState)

    g.add_node("researcher", researcher_node)
    g.add_node("retriever", retriever_node)
    g.add_node("writer_x", _make_writer_node("x"))
    g.add_node("writer_reddit", _make_writer_node("reddit"))
    g.add_node("writer_linkedin", _make_writer_node("linkedin"))
    g.add_node("critic", critic_node)
    g.add_node("finalize", finalize_node)

    g.add_edge(START, "researcher")
    g.add_edge("researcher", "retriever")

    def _route_to_writers(state: ContentState) -> list[str]:
        platforms = state.get("target_platforms", [])
        return [f"writer_{p}" for p in platforms] or ["writer_x"]

    g.add_conditional_edges(
        "retriever",
        _route_to_writers,
        {
            "writer_x": "writer_x",
            "writer_reddit": "writer_reddit",
            "writer_linkedin": "writer_linkedin",
        },
    )
    for writer in ("writer_x", "writer_reddit", "writer_linkedin"):
        g.add_edge(writer, "critic")
    g.add_edge("critic", "finalize")
    g.add_edge("finalize", END)

    return g.compile()


async def run_content_graph(initial_state: ContentState) -> ContentState:
    graph = build_content_graph()
    run_id = initial_state["run_id"]
    await _emit(run_id, kind="info", message="Graph started",
                data={"platforms": initial_state.get("target_platforms", [])})
    try:
        result: ContentState = await graph.ainvoke(initial_state)
        await _emit(run_id, kind="info", message="Graph finished")
        return result
    finally:
        _SEQUENCE_COUNTERS.pop(run_id, None)


__all__ = ["build_content_graph", "run_content_graph"]
