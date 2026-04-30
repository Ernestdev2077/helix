"""System prompt builders for writer agents.

Prompts incorporate:
- Platform-specific best practices (length, tone, format)
- KB context from brand docs (RAG)
- Few-shot references (liked posts)
- Active style rules (approved by user via Curator flow)

Everything is declarative so prompts remain inspectable and versionable.
"""

from __future__ import annotations

from typing import Any, Literal

Platform = Literal["x", "reddit", "linkedin"]


PLATFORM_RULES: dict[Platform, str] = {
    "x": """You write for X (Twitter). Constraints:
- Max 280 characters per post. If the idea is longer, split into a thread and number tweets.
- Open with a concrete hook: a surprising number, a crisp question, or a bold claim.
- No corporate buzzwords (synergy, leverage, unlock, empower, transform).
- One emoji max per tweet — only if it genuinely helps, never decorative.
- Hashtags: 0-2, placed at the end, lowercase unless the brand is CamelCase.""",
    "reddit": """You write for Reddit. Constraints:
- Respect subreddit culture: be genuine, not promotional. If self-promo is not allowed, tell a story instead.
- Structure: hook paragraph (why should they care) + body (specific details) + ask (what you want from readers).
- No marketing-speak. Sound like a human engineer/maker, not a marketer.
- Length: 150-600 words typically. Longer is fine if each paragraph adds value.
- Use markdown formatting (bold for emphasis, lists for clarity) but don't overdo it.""",
    "linkedin": """You write for LinkedIn. Constraints:
- Length: 800-1500 characters usually performs best. Short posts under 150 chars underperform.
- Strong first line — it's all people see before "see more". Make them click.
- One thought per paragraph, blank lines between. No walls of text.
- Professional tone but not stiff. Personal anecdotes and specific numbers travel well.
- Emoji: sparingly, at paragraph starts for visual anchoring, never gratuitous.""",
}


def _format_references(refs: list[dict[str, Any]], limit: int = 3) -> str:
    if not refs:
        return "(no references available yet — rely on platform best practices)"
    lines = []
    for i, ref in enumerate(refs[:limit], 1):
        text = ref.get("raw_text", "")[:400]
        metrics = ref.get("source_metrics") or {}
        hint = (
            f" (gained {metrics['likes']} likes)" if "likes" in metrics else ""
        )
        lines.append(f"{i}.{hint}\n{text}")
    return "\n\n".join(lines)


def _format_rules(rules: list[dict[str, Any]]) -> str:
    if not rules:
        return "(no learned style rules yet)"
    return "\n".join(f"- {r.get('rule_text', '')}" for r in rules)


VARIANT_DIRECTIONS = {
    "A": "Take the most direct, on-brand interpretation of the brief.",
    "B": "Take a notably DIFFERENT angle — different opening, different hook style, different rhythm. This is the A/B test counterpart to variant A, so contrast matters.",
    "C": "Take a third angle — try a story-format or contrarian take.",
    "D": "Take a fourth angle — try a thread/list format if the platform supports it.",
}


def writer_prompt(
    *,
    platform: Platform,
    kb_context: str = "",
    references: list[dict[str, Any]] | None = None,
    style_rules: list[dict[str, Any]] | None = None,
    variant_label: str = "A",
) -> str:
    references = references or []
    style_rules = style_rules or []

    rules_block = PLATFORM_RULES.get(platform, "")
    kb_block = kb_context.strip() or "(no brand knowledge base context retrieved)"
    refs_block = _format_references(references)
    style_block = _format_rules(style_rules)
    variant_direction = VARIANT_DIRECTIONS.get(variant_label, VARIANT_DIRECTIONS["A"])

    return f"""You are a senior social media strategist writing for a SaaS product.

{rules_block}

BRAND CONTEXT (what the product is, who it's for):
{kb_block}

LEARNED STYLE RULES (approved by the team based on past wins):
{style_block}

REFERENCES (posts that performed well for similar briefs):
{refs_block}

VARIANT DIRECTION (you are writing variant "{variant_label}"):
{variant_direction}

OUTPUT FORMAT:
Return only the post content. No preamble, no markdown fences, no meta-commentary, no explanations.
Do not output the platform name or the variant label."""


def writer_user_prompt(
    *, brief: str, goals: list[str], tone_hints: list[str]
) -> str:
    goals_str = ", ".join(goals) if goals else "(not specified)"
    tone_str = ", ".join(tone_hints) if tone_hints else "(use platform defaults)"
    return f"""BRIEF:
{brief}

PRIMARY GOALS: {goals_str}
TONE HINTS: {tone_str}

Write the post now."""
