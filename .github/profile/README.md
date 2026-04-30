<div align="center">

# 🧬 helix

_Agent-native SMM workspace for X / Reddit / LinkedIn._

</div>

We're developers who ship products fast but struggle to actually distribute them. So we built a tool that treats content the same way we treat code: an agent-based workflow with visible state, declarative rules, and a learning loop that gets noticeably better every week.

## What lives here

- **[helix](https://github.com/cookiedclaw/helix)** — the main monorepo (backend / agents / frontend).
- **[helix-landing](https://github.com/cookiedclaw/helix-landing)** — pitch page _(planned)_.
- **[helix/.github](https://github.com/cookiedclaw/.github)** — this profile.

## How it works in 30 seconds

1. Write a brief in natural language ("announcing feature X for indie devs, tone: ironic").
2. Agents draft platform-specific posts for X / Reddit / LinkedIn in parallel — pulling brand knowledge and your liked references into the prompt.
3. You watch the run live in the agent timeline. Cmd+K rewrites any selection.
4. Approve, schedule, or publish. A/B variants and bandit allocation come for free.
5. A Curator agent extracts declarative style rules from your wins and shows them to you with evidence — approve and they shape future drafts. Inspectable, reversible, never black-box.

## Status

Early development — backend, agent service, and frontend skeletons run end-to-end (stub LLM mode). OAuth connectors and real publishing land next. See the main repo's roadmap.

---

<div align="center">

made in Bishkek · 🧬

</div>
