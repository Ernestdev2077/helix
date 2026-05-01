"""Single source of truth for all helix prompts.

Six prompt builders, all sharing one SYSTEM_IDENTITY and one HUMAN_VOICE_FOOTER
so a generic-AI guardrail can never be forgotten:

  1. system_prompt()         — global identity (used by every other prompt)
  2. generation_prompt()     — write a variant for a platform with explicit hook
  3. ab_variation_prompt()   — reframe a winning post with N psych triggers
  4. learning_prompt()       — analyze winner vs siblings, extract patterns
  5. evolution_prompt()      — generation framing that applies learnings as
                               hard constraints (auto-selected by content_graph
                               when there are approved rules + patterns)
  6. reference_dna_prompt()  — extract a writing-DNA JSON from a reference

Why prompts as code: prompts are short, change frequently and benefit from
type checking and code review. PromptVersion (DB) is reserved for prompt
evolution where we need history + A/B of prompts themselves.
"""

from __future__ import annotations

from typing import Any, Literal

Platform = Literal["x", "reddit", "linkedin"]


# ---------------------------------------------------------------------------
# Identity + guardrails — folded into every system prompt
# ---------------------------------------------------------------------------

SYSTEM_IDENTITY = """You are an elite SMM strategist and copywriter.

Your job is NOT just to write posts.
Your job is to generate high-performing social media content that maximizes
engagement, reach, and conversions.

You always:
- adapt content to the platform (Twitter/X, Reddit, LinkedIn)
- write like a native user of each platform
- focus on hook -> value -> payoff
- avoid generic AI tone
- use specific, concrete language
- optimize for curiosity and clarity

You NEVER:
- write vague or generic content
- reuse the same structure across variants
- sound robotic or corporate

You generate distinct variants designed for A/B testing.
Each variant must:
- have a different hook style
- test a different angle (controversial, curiosity, value, story, etc.)

Output is concise, structured, and ready to post."""


# Phrases that immediately mark a post as AI-written. The footer instructs
# the model to avoid them; the critic also flags them post-hoc as warnings.
GENERIC_AI_PHRASES: list[str] = [
    "unleash",
    "dive into",
    "embark",
    "revolutionize",
    "transform",
    "synergy",
    "leverage",
    "unlock",
    "delve",
    "seamless",
    "pivotal",
    "paradigm",
    "tapestry",
    "in the realm of",
    "in the landscape of",
    "navigate the",
    "in today's fast-paced",
    "game-changing",
    "elevate your",
    "supercharge",
    "i'm thrilled to announce",
    "we are excited to announce",
    "say goodbye to",
    "ready to take",
    "hot take:",  # banned only as an opening cliché — see critic for context
]


def _format_phrase_list(phrases: list[str]) -> str:
    return "\n".join(f"  - {p}" for p in phrases)


HUMAN_VOICE_FOOTER = f"""HUMAN VOICE GUARDRAIL (applies to all output):
Avoid generic AI phrases. Write like a real human posting from a laptop at
2am, not a marketing department.

Specifically, do NOT use any of these phrases unless quoting someone:
{_format_phrase_list(GENERIC_AI_PHRASES)}

If a sentence sounds like LinkedIn-influencer or ChatGPT default tone,
rewrite it. Prefer concrete numbers, specific names, and tiny everyday details
over abstract benefits."""


def compose_system(*parts: str) -> str:
    """Join system-prompt blocks with the identity at the top and the human
    voice footer at the bottom — guarantees both are always present."""
    blocks = [SYSTEM_IDENTITY]
    for p in parts:
        if p and p.strip():
            blocks.append(p.strip())
    blocks.append(HUMAN_VOICE_FOOTER)
    return "\n\n".join(blocks)


# ---------------------------------------------------------------------------
# Platform rules
# ---------------------------------------------------------------------------

PLATFORM_RULES: dict[Platform, str] = {
    "x": """PLATFORM: X / Twitter
- Max 280 characters per post. If the idea is longer, split into a numbered thread.
- First line is everything: hook in <= 80 chars.
- One emoji max per tweet, only if it actively helps. No decorative emoji.
- Hashtags: 0-2, end of post, lowercase unless brand is CamelCase.
- No buzzwords. No corporate voice. Read it aloud — would a smart developer post this?""",
    "reddit": """PLATFORM: Reddit
- Respect subreddit culture: be genuine, never promotional. If self-promo is
  not allowed in the target sub, frame as a story or question instead.
- Structure: hook paragraph (why care) -> body (specific details, numbers, names)
  -> ask (what you want from readers).
- 150-600 words typically. Longer is fine if every paragraph adds value.
- Markdown for emphasis (bold, lists) — but don't over-format.
- Sound like a maker / engineer who happens to be sharing — not a marketer.""",
    "linkedin": """PLATFORM: LinkedIn
- 800-1500 chars usually performs best. Anything under 150 chars dies.
- First line decides everything (it's all visible before "see more").
- One thought per paragraph, blank lines between. No walls of text.
- Personal anecdote + concrete numbers + clear takeaway > generic insight.
- Professional but not stiff. Emoji sparingly at paragraph anchors, never gratuitous.""",
}


# ---------------------------------------------------------------------------
# Hook strategies — variant index -> (name, instruction)
# ---------------------------------------------------------------------------

HOOK_STRATEGIES: list[dict[str, str]] = [
    {
        "name": "curiosity",
        "directive": (
            "Open with a specific, slightly mysterious detail that creates an "
            "information gap. Tease — don't summarize. The reader must feel "
            "they will miss something if they scroll past."
        ),
    },
    {
        "name": "controversy",
        "directive": (
            "Open with a bold contrarian claim that names a common belief and "
            "calls it wrong. Disagree with conventional wisdom. Be punchy, "
            "not edgy for the sake of it — back the take with a real reason."
        ),
    },
    {
        "name": "story",
        "directive": (
            "Open with a tiny concrete moment in time — a specific user, a "
            "specific bug, a specific number, a specific message. Tell what "
            "happened, then deliver the lesson. No abstractions in line one."
        ),
    },
    {
        "name": "specificity",
        "directive": (
            "Open with a concrete number, percentage, or named outcome that "
            "anchors the post in reality. Numbers stop the scroll."
        ),
    },
    {
        "name": "emotional",
        "directive": (
            "Open with a feeling the audience knows but rarely sees written "
            "down — frustration, relief, smugness about a tiny win. Earn it "
            "with a specific cause, not vague platitudes."
        ),
    },
]


def hook_for_index(index: int) -> dict[str, str]:
    return HOOK_STRATEGIES[index % len(HOOK_STRATEGIES)]


# Psychological triggers used by A/B variation
AB_TRIGGERS: list[dict[str, str]] = [
    {
        "name": "curiosity",
        "directive": "Reframe to maximize information-gap. Tease, don't reveal.",
    },
    {
        "name": "controversy",
        "directive": "Reframe as a contrarian take. Name what most people think and call it wrong.",
    },
    {
        "name": "specificity",
        "directive": "Reframe around concrete numbers / named users / specific moments.",
    },
    {
        "name": "emotional",
        "directive": "Reframe to hit a felt frustration or small relief the audience knows.",
    },
]


# ---------------------------------------------------------------------------
# Helpers — formatting context blocks
# ---------------------------------------------------------------------------

def _format_references(refs: list[dict[str, Any]], limit: int = 3) -> str:
    if not refs:
        return "(no references available yet — rely on platform best practices)"
    lines = []
    for i, ref in enumerate(refs[:limit], 1):
        text = ref.get("raw_text", "")[:400]
        metrics = ref.get("source_metrics")
        if not isinstance(metrics, dict):
            metrics = {}
        feats = ref.get("extracted_features")
        if not isinstance(feats, dict):
            feats = {}
        bits = []
        if metrics.get("likes"):
            bits.append(f"{metrics['likes']} likes")
        if feats.get("tone"):
            bits.append(f"tone: {feats['tone']}")
        if feats.get("hook_patterns"):
            bits.append(f"hook: {feats['hook_patterns']}")
        hint = f" ({', '.join(bits)})" if bits else ""
        lines.append(f"{i}.{hint}\n{text}")
    return "\n\n".join(lines)


def _format_rules(rules: list[dict[str, Any]]) -> str:
    if not rules:
        return "(no learned style rules yet)"
    return "\n".join(f"- {r.get('rule_text', '')}" for r in rules)


def _format_winning_patterns(patterns: list[dict[str, Any]]) -> str:
    if not patterns:
        return ""
    lines = []
    for p in patterns[:5]:
        lift = p.get("lift", 0)
        sample = p.get("sample_size", 0)
        lines.append(f"- {p.get('pattern_text', '')} (+{lift*100:.0f}%, n={sample})")
    return "\n".join(lines)


def _format_brand_dna(dna: dict[str, Any] | None) -> str:
    if not dna:
        return ""
    parts = []
    if dna.get("tone"):
        parts.append(f"Tone: {dna['tone']}")
    if dna.get("structure"):
        parts.append(f"Structure: {dna['structure']}")
    if dna.get("hook_patterns"):
        parts.append(f"Hook patterns: {dna['hook_patterns']}")
    return "\n".join(parts)


def _format_brand_kb(kb_context: str) -> str:
    return kb_context.strip() or "(no brand knowledge base context yet)"


# ---------------------------------------------------------------------------
# 1. system_prompt — bare identity (used standalone for sub-prompts)
# ---------------------------------------------------------------------------

def system_prompt() -> str:
    """The bare global identity. All other system prompts compose from this
    via compose_system() so the human-voice footer is also guaranteed."""
    return compose_system()


# ---------------------------------------------------------------------------
# 2. generation_prompt — write one variant
# ---------------------------------------------------------------------------

def generation_prompt(
    *,
    platform: Platform,
    variant_index: int = 0,
    kb_context: str = "",
    references: list[dict[str, Any]] | None = None,
    style_rules: list[dict[str, Any]] | None = None,
    winning_patterns: list[dict[str, Any]] | None = None,
    brand_dna: dict[str, Any] | None = None,
    use_evolution_framing: bool = False,
) -> tuple[str, str]:
    """Returns (system_prompt, hook_strategy_name) — caller uses hook name to
    label the persisted variant for UI ("curiosity hook" etc.)."""
    references = references or []
    style_rules = style_rules or []
    winning_patterns = winning_patterns or []

    hook = hook_for_index(variant_index)
    rules_block = PLATFORM_RULES.get(platform, "")
    kb_block = _format_brand_kb(kb_context)
    refs_block = _format_references(references)
    style_block = _format_rules(style_rules)
    patterns_block = _format_winning_patterns(winning_patterns)
    dna_block = _format_brand_dna(brand_dna)

    if use_evolution_framing and (style_rules or winning_patterns):
        learnings_section = f"""APPROVED STYLE RULES (HARD CONSTRAINTS — must follow):
{style_block}

WINNING PATTERNS FROM PAST A/B TESTS (apply these — they outperformed):
{patterns_block or '(none yet)'}

You are evolving the brand's content strategy based on real performance data.
The rules above are not suggestions; treat them as constraints. Variants must
still differ from each other (use the hook strategy below), but every variant
must follow the rules."""
    else:
        learnings_section = f"""LEARNED STYLE RULES (use as guidance):
{style_block}"""

    hook_section = f"""HOOK STRATEGY (you are writing the "{hook['name']}" variant):
{hook['directive']}"""

    brand_section = f"""BRAND CONTEXT:
{kb_block}"""
    if dna_block:
        brand_section += f"\n\nBRAND WRITING DNA (aggregated from references):\n{dna_block}"

    refs_section = f"""REFERENCES (posts that performed well for similar briefs):
{refs_block}"""

    output_section = """OUTPUT FORMAT:
Return ONLY the post content. No preamble. No markdown fences. No platform
name. No variant label. No meta-commentary or explanations."""

    system = compose_system(
        rules_block,
        brand_section,
        learnings_section,
        refs_section,
        hook_section,
        output_section,
    )
    return system, hook["name"]


def generation_user_prompt(
    *, brief: str, goals: list[str], tone_hints: list[str]
) -> str:
    goals_str = ", ".join(goals) if goals else "(not specified)"
    tone_str = ", ".join(tone_hints) if tone_hints else "(use platform defaults)"
    return f"""BRIEF:
{brief}

PRIMARY GOALS: {goals_str}
TONE HINTS: {tone_str}

Write the post now."""


# ---------------------------------------------------------------------------
# 3. ab_variation_prompt — reframe a winning post N times
# ---------------------------------------------------------------------------

def ab_variation_prompt(
    *,
    original_post: str,
    platform: Platform,
    trigger_index: int = 0,
    kb_context: str = "",
    style_rules: list[dict[str, Any]] | None = None,
) -> tuple[str, str]:
    style_rules = style_rules or []
    trigger = AB_TRIGGERS[trigger_index % len(AB_TRIGGERS)]

    rules_block = PLATFORM_RULES.get(platform, "")
    style_block = _format_rules(style_rules)
    kb_block = _format_brand_kb(kb_context)

    instructions = f"""TASK: Reframe the "ORIGINAL POST" below for A/B testing.

You are generating ONE alternate version with a different psychological trigger.

PSYCHOLOGICAL TRIGGER FOR THIS VARIANT: "{trigger['name']}"
Directive: {trigger['directive']}

Each reframing MUST:
- Keep the core idea / promise of the original
- Change the hook significantly (not paraphrase)
- Feel like a different strategy, not a rewording
- Stay native to the platform

Do NOT make small edits. Make it feel like a different strategy entirely."""

    output_section = """OUTPUT FORMAT:
Return ONLY the new post content. No preamble. No markdown fences. No labels."""

    system = compose_system(
        rules_block,
        f"BRAND CONTEXT:\n{kb_block}",
        f"LEARNED STYLE RULES:\n{style_block}",
        instructions,
        output_section,
    )

    user = f"""ORIGINAL POST:
{original_post}

Now write the alternate version using the "{trigger['name']}" trigger."""
    return system, trigger["name"]


def ab_variation_user(*, original_post: str, trigger_name: str) -> str:
    return f"""ORIGINAL POST:
{original_post}

Now write the alternate version using the "{trigger_name}" trigger."""


# ---------------------------------------------------------------------------
# 4. learning_prompt — analyze winner vs siblings, extract patterns
# ---------------------------------------------------------------------------

def learning_prompt() -> str:
    """System prompt for the curator's winner-vs-siblings analysis."""
    instructions = """TASK: You are analyzing why one social media post variant won an A/B test.

You will be given:
- BRAND context
- One or more "winner vs siblings" cases — for each case, the variant the team
  starred (winner) and the other variants from the same brief that were not starred
- Existing references the team has liked

Output 1 to 3 SHORT, ACTIONABLE patterns explaining what made winners win.
Each pattern must be supported by AT LEAST 2 cases (across winners or refs).

OUTPUT STRICT JSON:
{
  "winning_patterns": [
    {
      "pattern_text": "imperative, 5-15 words, e.g. 'Open with a specific user handle or first name'",
      "rationale": "1-2 sentences referencing which winners/refs support this",
      "platform": "" | "x" | "reddit" | "linkedin",
      "metric": "engagement_rate",
      "lift": 0.20-2.00,
      "sample_size": <int>,
      "evidence_winner_ids": ["<variant uuid>", ...]
    }
  ],
  "proposed_rules": [
    {
      "rule_text": "imperative, 5-15 words, derived from a winning pattern",
      "rationale": "why",
      "scope": "global" | "platform",
      "platform": "" | "x" | "reddit" | "linkedin",
      "confidence": 0.0-1.0,
      "evidence_reference_ids": ["<reference uuid>", ...]
    }
  ]
}

Return {"winning_patterns": [], "proposed_rules": []} if data is too thin."""

    return compose_system(instructions)


def learning_user(
    *,
    brand: dict[str, Any],
    winner_cases: list[dict[str, Any]],
    references: list[dict[str, Any]],
) -> str:
    cases_block = "\n\n".join(_format_winner_case(i + 1, c) for i, c in enumerate(winner_cases[:5]))
    refs_block = _format_references(references, limit=10)

    return f"""BRAND: {brand.get('name', '?')}
DESCRIPTION: {brand.get('description', '')}
VOICE DO: {brand.get('voice_do') or []}
VOICE DON'T: {brand.get('voice_dont') or []}

WINNER vs SIBLINGS CASES:
{cases_block or '(no A/B winners with siblings yet)'}

LIKED REFERENCES:
{refs_block}

Extract patterns now."""


def _format_winner_case(num: int, case: dict[str, Any]) -> str:
    winner = case.get("winner") or {}
    siblings = case.get("siblings") or []
    parts = [
        f"CASE [{num}] (platform={winner.get('platform', '?')}, brief='{case.get('brief', '')[:80]}')"
    ]
    parts.append(f"WINNER (id={winner.get('id', '')}):\n{winner.get('content', '')[:500]}")
    for j, sib in enumerate(siblings[:3], 1):
        parts.append(f"SIBLING {j} (id={sib.get('id', '')}, NOT starred):\n{sib.get('content', '')[:500]}")
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# 5. evolution_prompt — already wired into generation_prompt(use_evolution_framing=True)
# ---------------------------------------------------------------------------
# Kept as a named export for clarity; just delegates.

def evolution_prompt(
    *,
    platform: Platform,
    variant_index: int = 0,
    kb_context: str = "",
    references: list[dict[str, Any]] | None = None,
    style_rules: list[dict[str, Any]] | None = None,
    winning_patterns: list[dict[str, Any]] | None = None,
    brand_dna: dict[str, Any] | None = None,
) -> tuple[str, str]:
    return generation_prompt(
        platform=platform,
        variant_index=variant_index,
        kb_context=kb_context,
        references=references,
        style_rules=style_rules,
        winning_patterns=winning_patterns,
        brand_dna=brand_dna,
        use_evolution_framing=True,
    )


# ---------------------------------------------------------------------------
# 6. reference_dna_prompt — extract a writing-DNA JSON from a reference
# ---------------------------------------------------------------------------

def reference_dna_prompt() -> str:
    instructions = """TASK: Analyze the writing style of one reference post.

Extract a compact "writing DNA" — what makes this post sound the way it does.
Be specific. Avoid generic adjectives ("good", "engaging", "effective").

OUTPUT STRICT JSON, no prose, no markdown:
{
  "tone": "1 sentence describing the voice (specific adjectives)",
  "structure": "1 sentence describing the post's shape (hook -> body -> ask, list, story arc, etc.)",
  "hook_patterns": "1 sentence on how it opens (concrete number, question, contrarian claim, time-anchor, etc.)",
  "style_rules": [
    "imperative, 5-15 words, learnable rule extracted from this post",
    "..."
  ],
  "key_phrases": ["1-3 short phrases that anchor the voice"]
}

Return at most 3 style_rules. Quality over quantity."""
    return compose_system(instructions)


def reference_dna_user(*, reference_text: str, platform: str) -> str:
    return f"""PLATFORM: {platform or 'unknown'}

REFERENCE POST:
{reference_text[:1500]}

Extract the writing DNA now as JSON."""


# ---------------------------------------------------------------------------
# Critic — phrase-list scanner used by content_graph.critic_node
# ---------------------------------------------------------------------------

def detect_generic_phrases(text: str) -> list[str]:
    """Return banned phrases found in the text (case-insensitive substring)."""
    lower = text.lower()
    return [p for p in GENERIC_AI_PHRASES if p in lower]


__all__ = [
    "Platform",
    "SYSTEM_IDENTITY",
    "GENERIC_AI_PHRASES",
    "HUMAN_VOICE_FOOTER",
    "PLATFORM_RULES",
    "HOOK_STRATEGIES",
    "AB_TRIGGERS",
    "compose_system",
    "system_prompt",
    "generation_prompt",
    "generation_user_prompt",
    "ab_variation_prompt",
    "ab_variation_user",
    "learning_prompt",
    "learning_user",
    "evolution_prompt",
    "reference_dna_prompt",
    "reference_dna_user",
    "detect_generic_phrases",
    "hook_for_index",
]
