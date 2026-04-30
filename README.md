<div align="center">

# 🧬 helix

_Agent-native SMM workspace. Multi-agent SaaS for X / Reddit / LinkedIn with a transparent learning loop._

</div>

> [!WARNING]
> **Early development.** Backend, agent service, and frontend skeletons run end-to-end (graph generates stub variants for X / Reddit / LinkedIn). OAuth connectors, real publishing, Curator agent, and the prompt-evolution layer are not wired yet — see roadmap below.

## What this is

A multi-tenant SaaS that turns a single brief into A/B-tested posts for X, Reddit, and LinkedIn — and gets noticeably better at it every week. Think of it as Cursor for SMM specialists: a Composer in the middle, a live agent timeline on the right, a Library of references and learned style rules on the left.

The product owns:

- **Composer** — type a brief, agents draft adapted posts per platform in parallel, you watch the graph run in a live timeline (WebSocket from Django Channels). Cmd+K inline edits, ghost suggestions, character / readability indicators per platform.
- **Reference Library** — paste URLs of posts you like; a parser pulls text + media + source metrics. Each reference becomes few-shot context the writers retrieve from. A/B winners auto-promote here in one click.
- **Style Rules** — a Curator agent extracts declarative rules ("open with a concrete number in line one") from liked references and significant A/B wins, with evidence. You approve / edit / reject — approved rules get injected into writer prompts. Inspectable, reversible, never black-box.
- **A/B + bandit** — variants are first-class. Phase 1: 50/50 split with χ² significance. Phase 2: Thompson sampling allocates traffic to winning variants for recurring content.
- **Multi-platform publishing** — `tweepy` (X), `PRAW` (Reddit) with per-subreddit anti-promo rules in the Critic, LinkedIn Marketing API. Celery scheduler with retries.
- **Per-workspace prompt evolution + optional LoRA** — once a workspace has ≥ 200 publications with metrics, writer prompts are auto-optimized on `(brief → winner)` pairs (DSPy-style). Premium tier: per-workspace LoRA on open-source models, never cross-tenant.

## Stack

- **backend** — Django 5 + DRF + Channels (WebSocket) + Celery + Postgres + pgvector
- **agents** — FastAPI + LangGraph + LiteLLM (multi-provider routing) + LangSmith (tracing)
- **frontend** — Vue 3 + TypeScript + Vite + Tailwind + Pinia + TipTap + motion-v
- **infra** — docker-compose (dev), Stripe + dj-stripe (billing), Sentry, S3-compatible object storage

## Architecture

```
                                                              ┌───────────┐
                                                              │ Postgres  │
                                                              │ +pgvector │
                                                              └─────▲─────┘
                                                                    │
   ┌─────────────┐    HTTPS        ┌──────────────────────┐         │
   │ Vue SPA     │ ──────────────► │  Django + Channels   │         │
   │ (composer,  │ ◄────WS─────────│  (REST + WS, ASGI)   │ ────────┤
   │  library,   │                 └──────────┬───────────┘         │
   │  analytics) │                            │ pub/sub             │
   └─────────────┘                            ▼                     │
                                       ┌─────────────┐              │
                                       │    Redis    │              │
                                       └──────┬──────┘              │
                                              │ subscribe           │
                                              ▼                     │
                                  ┌──────────────────────────┐      │
                                  │   helix-agents (FastAPI) │      │
                                  │   LangGraph orchestrator │ ─────┘
                                  │   ┌─ Researcher ──────┐  │
                                  │   ├─ Retriever (RAG)  │  │
                                  │   ├─ Writer per X/R/L │  │
                                  │   ├─ Critic           │  │
                                  │   ├─ Curator          │  │
                                  │   └─ Analyst          │  │
                                  └──────────────────────────┘
```

When the user hits **Run** in the composer, Django creates an `AgentRun`, posts to the agent service, and returns a `run_id`. The SPA subscribes via WebSocket to `/ws/agent-runs/<run_id>/` — Django Channels relays events from Redis (published by LangGraph nodes) to the client in real time. Replay events for late joiners are fetched from the `AgentEvent` table.

## Repo layout

```
helix/
├── backend/         Django 5, 8 apps (workspaces, brands, content, publishing, analytics,
│                    agent_runs, billing, accounts), 22 models, multi-tenancy middleware,
│                    DRF endpoints, Channels consumer, Celery worker + beat
├── agents/          FastAPI service. graphs/content_graph.py runs:
│                    researcher → retriever → writer×3 (parallel) → critic → finalize.
│                    Streams events to Redis; LiteLLM routes models per node.
├── frontend/        Vue 3 + TS SPA. AppLayout (sidebar / topbar / agent panel),
│                    Composer, Library (Style Rules learned + references grid),
│                    Calendar, Analytics, Brand, Settings, Auth, Onboarding.
├── infra/docker/    Dockerfiles per service.
├── docker-compose.yml
├── Makefile
└── .env.example
```

## Run it (development)

Requires Docker + Docker Compose.

```bash
make setup            # copy .env.example → .env; fill in DJANGO_SECRET_KEY at minimum.
                      # OPENAI_API_KEY or ANTHROPIC_API_KEY enable real generation —
                      # without them, writers return labeled stub content.

make up               # start postgres+pgvector, redis, backend, agents, 2x celery, frontend
make backend-migrate  # run Django migrations (first time only)
make backend-superuser

# Then open:
#   http://localhost:5173    — frontend
#   http://localhost:8000/admin/  — Django admin
#   http://localhost:8001/health  — agent service
```

`make logs` tails all services. `make down` stops them. `make clean` wipes volumes.

### Without Docker

Postgres (with `vector` extension) and Redis must already be running locally.

```bash
# backend
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8000

# agents (separate terminal)
cd agents && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn agents.main:app --reload --port 8001

# frontend (separate terminal)
cd frontend && npm install && npm run dev
```

## API surface

All under `/api/v1/`. JWT in `Authorization: Bearer <token>`. Active workspace via `X-Workspace: <uuid-or-slug>` header (resolved by `apps.workspaces.middleware.WorkspaceContextMiddleware`).

| resource              | endpoint                                              |
| --------------------- | ----------------------------------------------------- |
| auth                  | `/auth/login/` · `/auth/registration/` · `/auth/logout/` |
| workspaces            | `/workspaces/` · `/workspaces/<id>/members/`          |
| invites               | `/workspaces/invites/`                                |
| brands + KB           | `/brands/` · `/brands/documents/`                     |
| campaigns             | `/content/campaigns/`                                 |
| posts                 | `/content/posts/` · `POST /<id>/generate/`            |
| variants              | `/content/variants/`                                  |
| references            | `/content/references/`                                |
| style rules           | `/content/style-rules/` · `POST /<id>/approve/`       |
| winning patterns      | `/content/winning-patterns/`                          |
| platform accounts     | `/publishing/accounts/`                               |
| publications          | `/publishing/publications/`                           |
| metrics               | `/analytics/metrics/`                                 |
| bandit state          | `/analytics/bandit/`                                  |
| agent runs            | `/agent-runs/` · `/agent-runs/<id>/events/`           |
| billing               | `/billing/subscription/current/`                      |

WebSocket: `ws://localhost:8000/ws/agent-runs/<uuid>/` — streams `AgentEvent`s including replay.

## The learning loop

Three levels of learning, all inspectable, all per-workspace, never cross-tenant.

**Level 1 · Few-shot retrieval (instant).** Writer agents get top-K references and prior A/B winners injected into their prompt via hybrid BM25 + pgvector search. Like a post → next draft already feels closer to it. No training.

**Level 2 · Curator → Style Rules (nightly).** A scheduled Curator agent reads recent liked references and statistically significant A/B winners, proposes declarative rules with evidence:

> _"Open with a concrete number in line one"_ — proposed
> Evidence: 7 liked refs + 3 A/B winners (+43% engagement) — confidence 0.82
> `[Approve]  [Reject]  [Edit]`

Approved rules get appended to writer system prompts per brand / platform. The user always sees what the system has learned and can edit it.

**Level 3 · Prompt evolution + optional LoRA (later, premium).** Once a workspace has ≥ 200 publications with metrics, writer prompts get DSPy-style auto-optimized on historical `(brief → winner)` pairs. Shadow runs validate before promotion. For large workspaces, optional LoRA fine-tune on open-source models (Llama 3 / Qwen) hosted via vLLM — strictly per-workspace, no pooled training.

## Roadmap

- **Foundation** — _shipped:_ monorepo, Django + 8 apps + 22 models, FastAPI agent service, content graph runs end-to-end (stub mode), Vue 3 SPA with auth / app layout / composer / library skeletons, docker-compose, multi-tenancy middleware.
- **Brand KB ingest + RAG** — chunk uploaded docs, embed to pgvector, retriever node pulls relevant context.
- **X vertical slice** — OAuth flow, `tweepy` connector, real publishing, metric snapshots from X API v2.
- **Composer interactions** — TipTap editor with Cmd+K inline edits, ghost suggestions, "Inspired by" panel showing actual retrieved references and active rules.
- **Reddit + LinkedIn writer agents** — `PRAW`-based with per-subreddit rules engine, LinkedIn personal posting via `w_member_social`.
- **A/B + bandit** — `PostVariant.allocation_weight`, Celery task for Thompson sampling, statistical-significance UI in Analytics.
- **Curator agent** — extracts `StyleRule`s from liked refs and A/B winners; proposed-rule cards in Library with approve / reject / edit.
- **Analyst agent** — winning patterns, "promote to rule" CTA, model-evolution timeline in Analytics.
- **Prompt evolution** — versioned `PromptVersion` store, shadow runs, LLM-as-judge scoring; optional vLLM-backed LoRA endpoint behind LiteLLM.
- **Onboarding wizard** — 5-step flow (workspace → connect platforms → brand basics → seed the model → first post demo).
- **SaaS polish** — Stripe billing (per-seat + AI credits), team invites, landing page, deploy to Fly.io / Railway.
- **Frontend polish** — motion-v + auto-animate + GSAP, streaming typewriter in timeline / composer, spring-physics micro-interactions, shared element transitions, Lottie empty states. Bench against Linear / Vercel / Cursor.

## Related

- **helix-landing** — pitch page (planned)
- **helix/.github** — org profile (planned)

---

<div align="center">

made in Bishkek · proprietary · 🧬

</div>
