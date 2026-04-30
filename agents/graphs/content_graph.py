"""Content generation graph — LangGraph state machine.

Flow:
    START → researcher → retriever → writer×2 per platform (A/B fan-out, parallel)
          → critic → finalize → END

Each node publishes events via the Redis event bus so the UI can show a
live timeline. LLM calls go through LiteLLM (``litellm.acompletion``) for
provider routing — primarily OpenRouter.

After ``finalize``, results are POSTed to Django via the internal callback
endpoint to persist `PostVariant`s in DB.
"""

from __future__ import annotations

import itertools
import logging
from typing import Any

from langgraph.graph import END, START, StateGraph

from ..event_bus import get_bus
from ..prompts import system_prompts
from ..tools.db import fetch_active_rules, fetch_brand, fetch_references
from ..tools.django_api import report_content_completed
from ..tools.llm import chat_complete
from .state import ContentState, Platform, VariantDraft

log = logging.getLogger(__name__)

VARIANTS_PER_PLATFORM = 2  # A and B
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
# Researcher — load brand voice metadata
# ---------------------------------------------------------------------------
async def researcher_node(state: ContentState) -> dict[str, Any]:
    run_id = state["run_id"]
    brand_id = state.get("brand_id", "")
    await _emit(run_id, kind="node_started", node_name="researcher",
                message="Loading brand voice...")

    brand = await fetch_brand(brand_id) if brand_id else None
    if not brand:
        await _emit(run_id, kind="node_finished", node_name="researcher",
                    message="No brand found — using defaults")
        return {"kb_context": ""}

    do_list = ", ".join(brand.get("voice_do") or []) or "(none)"
    dont_list = ", ".join(brand.get("voice_dont") or []) or "(none)"
    kb = (
        f"Brand: {brand['name']}\n"
        f"Description: {brand.get('description') or '(none)'}\n"
        f"Audience: {brand.get('target_audience') or '(general)'}\n"
        f"Voice description: {brand.get('voice_description') or '(default)'}\n"
        f"Voice DO: {do_list}\n"
        f"Voice DON'T: {dont_list}"
    )
    await _emit(run_id, kind="node_finished", node_name="researcher",
                message=f"Loaded brand '{brand['name']}'")
    return {"kb_context": kb}


# ---------------------------------------------------------------------------
# Retriever — top references + active style rules per platform
# ---------------------------------------------------------------------------
async def retriever_node(state: ContentState) -> dict[str, Any]:
    run_id = state["run_id"]
    workspace_id = state["workspace_id"]
    brand_id = state.get("brand_id", "")
    platforms = state.get("target_platforms", [])

    await _emit(run_id, kind="node_started", node_name="retriever",
                message="Fetching references and style rules...")

    if not brand_id:
        await _emit(run_id, kind="node_finished", node_name="retriever",
                    message="No brand — skipping retrieval")
        return {"retrieved_references": [], "active_style_rules": []}

    refs: list[dict[str, Any]] = []
    rules: list[dict[str, Any]] = []
    for p in platforms:
        refs += await fetch_references(
            workspace_id=workspace_id, brand_id=brand_id, platform=p, limit=3
        )
        rules += await fetch_active_rules(
            workspace_id=workspace_id, brand_id=brand_id, platform=p
        )

    seen_ref_ids: set[str] = set()
    deduped_refs = []
    for r in refs:
        if r["id"] not in seen_ref_ids:
            seen_ref_ids.add(r["id"])
            deduped_refs.append(r)
    seen_rule_ids: set[str] = set()
    deduped_rules = []
    for r in rules:
        if r["id"] not in seen_rule_ids:
            seen_rule_ids.add(r["id"])
            deduped_rules.append(r)

    await _emit(
        run_id, kind="node_finished", node_name="retriever",
        message=f"Loaded {len(deduped_refs)} refs + {len(deduped_rules)} active rules",
        data={
            "ref_count": len(deduped_refs),
            "rule_count": len(deduped_rules),
            "rules_preview": [r["rule_text"][:80] for r in deduped_rules[:3]],
        },
    )
    return {"retrieved_references": deduped_refs, "active_style_rules": deduped_rules}


# ---------------------------------------------------------------------------
# Writer — generates VARIANTS_PER_PLATFORM drafts for one platform
# ---------------------------------------------------------------------------
def _make_writer_node(platform: Platform):
    async def writer_node(state: ContentState) -> dict[str, Any]:
        run_id = state["run_id"]
        await _emit(run_id, kind="node_started", node_name=f"writer_{platform}",
                    message=f"Drafting {VARIANTS_PER_PLATFORM} variants for {platform}...")

        variants_out: list[VariantDraft] = []
        labels = ["A", "B", "C", "D"]
        total_in = total_out = 0

        for i in range(VARIANTS_PER_PLATFORM):
            label = labels[i]
            system_prompt = system_prompts.writer_prompt(
                platform=platform,
                kb_context=state.get("kb_context", ""),
                references=state.get("retrieved_references", []),
                style_rules=state.get("active_style_rules", []),
                variant_label=label,
            )
            user_prompt = system_prompts.writer_user_prompt(
                brief=state["brief"],
                goals=state.get("goals", []),
                tone_hints=state.get("tone_hints", []),
            )
            try:
                response = await chat_complete(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    role="writer",
                    platform=platform,
                    temperature=0.85 + i * 0.1,  # diversify variant B
                )
                content = response["content"]
                tokens_in = response.get("tokens_in", 0)
                tokens_out = response.get("tokens_out", 0)
                total_in += tokens_in
                total_out += tokens_out
            except Exception as exc:  # noqa: BLE001
                log.exception("Writer failed for %s/%s", platform, label)
                content = f"[writer error: {exc}]"

            variants_out.append({
                "platform": platform,
                "label": label,
                "content": content.strip(),
                "critic_notes": [],
                "inspired_by_reference_ids": [
                    r["id"] for r in state.get("retrieved_references", [])
                    if r.get("platform") in (platform, "")
                ],
                "inspired_by_rule_ids": [
                    r["id"] for r in state.get("active_style_rules", [])
                ],
            })
            await _emit(
                run_id, kind="stream_chunk", node_name=f"writer_{platform}",
                message=f"Variant {label} ready ({len(content)} chars)",
                data={"platform": platform, "label": label,
                      "preview": content[:140]},
                tokens_in=tokens_in, tokens_out=tokens_out,
            )

        await _emit(
            run_id, kind="node_finished", node_name=f"writer_{platform}",
            message=f"Done — {len(variants_out)} variants",
            tokens_in=total_in, tokens_out=total_out,
        )
        return {"variants": variants_out}

    writer_node.__name__ = f"writer_{platform}"
    return writer_node


# ---------------------------------------------------------------------------
# Critic — quality / platform-compliance check (rule-based, fast)
# ---------------------------------------------------------------------------
async def critic_node(state: ContentState) -> dict[str, Any]:
    run_id = state["run_id"]
    await _emit(run_id, kind="node_started", node_name="critic",
                message="Reviewing all variants...")

    notes: list[dict[str, Any]] = []
    for v in state.get("variants", []):
        issues: list[dict[str, Any]] = []
        length = len(v["content"])
        platform = v["platform"]
        if platform == "x" and length > 280:
            issues.append({
                "severity": "error",
                "message": f"X post exceeds 280 chars ({length})",
                "fix_suggestion": "Shorten or split into a thread",
            })
        if platform == "linkedin" and length < 150:
            issues.append({
                "severity": "warn",
                "message": "LinkedIn posts under 150 chars tend to underperform",
                "fix_suggestion": "Add a concrete example or stat",
            })
        buzz = ["synergy", "leverage", "unlock", "empower", "transform"]
        found = [b for b in buzz if b in v["content"].lower()]
        if found:
            issues.append({
                "severity": "warn",
                "message": f"Buzzwords detected: {', '.join(found)}",
                "fix_suggestion": "Rephrase with concrete language",
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
# Finalize — persist back to Django + emit summary event
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
