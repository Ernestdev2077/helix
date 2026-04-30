"""Content generation graph — LangGraph state machine.

Flow:
    START → researcher → retriever → writer(s, parallel per platform)
          → critic → finalize → END

Each node publishes events via the Redis event bus so the UI can show a
live timeline. LLM calls go through LiteLLM (``litellm.acompletion``) for
provider routing.

This is a minimal but functional v1. Later we'll add:
- Curator feedback node (extract rules)
- Human approval gate with checkpointer
- Variants generator (A/B fan-out)
- Platform-specific post-processing
"""

from __future__ import annotations

import itertools
import logging
from typing import Any

from langgraph.graph import END, START, StateGraph

from ..event_bus import get_bus
from ..prompts import system_prompts
from ..tools.llm import chat_complete
from .state import ContentState, Platform, VariantDraft

log = logging.getLogger(__name__)

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
# Node: researcher — pull relevant KB chunks for the brief
# ---------------------------------------------------------------------------
async def researcher_node(state: ContentState) -> dict[str, Any]:
    run_id = state["run_id"]
    await _emit(run_id, kind="node_started", node_name="researcher",
                message="Searching brand knowledge base...")

    # TODO(rag): real pgvector similarity search. For now, return empty context.
    kb_context = ""
    await _emit(run_id, kind="node_finished", node_name="researcher",
                message="Found 0 relevant KB chunks (RAG not yet wired)")
    return {"kb_context": kb_context}


# ---------------------------------------------------------------------------
# Node: retriever — fetch top-K references + active style rules
# ---------------------------------------------------------------------------
async def retriever_node(state: ContentState) -> dict[str, Any]:
    run_id = state["run_id"]
    await _emit(run_id, kind="node_started", node_name="retriever",
                message="Fetching references and style rules...")

    # TODO(learning_loop): hybrid BM25 + vector search over Reference table,
    # plus active StyleRules filtered by brand/platform.
    retrieved = state.get("retrieved_references", [])
    rules = state.get("active_style_rules", [])
    await _emit(
        run_id, kind="node_finished", node_name="retriever",
        message=f"Loaded {len(retrieved)} refs + {len(rules)} active rules",
    )
    return {"retrieved_references": retrieved, "active_style_rules": rules}


# ---------------------------------------------------------------------------
# Node: writer — one per platform; composed via a platform-aware prompt
# ---------------------------------------------------------------------------
def _make_writer_node(platform: Platform):
    async def writer_node(state: ContentState) -> dict[str, Any]:
        run_id = state["run_id"]
        await _emit(run_id, kind="node_started", node_name=f"writer_{platform}",
                    message=f"Drafting {platform} post...")

        system_prompt = system_prompts.writer_prompt(
            platform=platform,
            kb_context=state.get("kb_context", ""),
            references=state.get("retrieved_references", []),
            style_rules=state.get("active_style_rules", []),
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
                platform=platform,
            )
            content = response["content"]
            tokens_in = response.get("tokens_in", 0)
            tokens_out = response.get("tokens_out", 0)
        except Exception as exc:  # noqa: BLE001
            log.exception("Writer failed for %s", platform)
            await _emit(run_id, kind="error", node_name=f"writer_{platform}",
                        message=str(exc))
            content = f"[writer error: {exc}]"
            tokens_in = tokens_out = 0

        variant: VariantDraft = {
            "platform": platform,
            "label": "A",
            "content": content,
            "critic_notes": [],
            "inspired_by_reference_ids": [
                r["id"] for r in state.get("retrieved_references", [])
            ],
            "inspired_by_rule_ids": [
                r["id"] for r in state.get("active_style_rules", [])
            ],
        }

        await _emit(
            run_id,
            kind="node_finished",
            node_name=f"writer_{platform}",
            message=f"Draft ready ({len(content)} chars)",
            data={"preview": content[:200]},
            tokens_in=tokens_in,
            tokens_out=tokens_out,
        )
        return {"variants": [variant]}

    writer_node.__name__ = f"writer_{platform}"
    return writer_node


# ---------------------------------------------------------------------------
# Node: critic — quality / platform-compliance check
# ---------------------------------------------------------------------------
async def critic_node(state: ContentState) -> dict[str, Any]:
    run_id = state["run_id"]
    await _emit(run_id, kind="node_started", node_name="critic",
                message="Reviewing drafts...")

    notes: list[dict[str, Any]] = []
    for v in state.get("variants", []):
        issues: list[dict[str, Any]] = []
        length = len(v["content"])
        if v["platform"] == "x" and length > 280:
            issues.append({
                "severity": "error",
                "message": f"X post exceeds 280 chars ({length})",
                "fix_suggestion": "Shorten or split into a thread",
            })
        if v["platform"] == "linkedin" and length < 150:
            issues.append({
                "severity": "warn",
                "message": "LinkedIn posts under 150 chars tend to underperform",
                "fix_suggestion": "Add a concrete example or stat",
            })
        v["critic_notes"] = issues
        notes.extend([{"platform": v["platform"], "label": v["label"], **i} for i in issues])

    passed = all(n["severity"] != "error" for n in notes)
    await _emit(
        run_id,
        kind="node_finished",
        node_name="critic",
        message=f"{'Passed' if passed else 'Found issues'} ({len(notes)} notes)",
        data={"notes": notes, "passed": passed},
    )
    return {"critic_pass": passed, "critic_notes": notes}


# ---------------------------------------------------------------------------
# Node: finalize — build output payload for the API
# ---------------------------------------------------------------------------
async def finalize_node(state: ContentState) -> dict[str, Any]:
    run_id = state["run_id"]
    output = {
        "variants": state.get("variants", []),
        "critic_pass": state.get("critic_pass", False),
        "critic_notes": state.get("critic_notes", []),
    }
    await _emit(
        run_id, kind="node_finished", node_name="finalize",
        message="Run complete", data={"variant_count": len(output["variants"])},
    )
    return {"output": output}


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------
def build_content_graph():
    """Compile the content generation graph.

    Writers per platform run in parallel (fan-out) and their results are
    merged via the ``Annotated[list, operator.add]`` on ``variants``.
    """
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
