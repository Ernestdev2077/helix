"""FastAPI entrypoint for the agent service.

Endpoints:
    POST /runs             — kick off a graph run (async, returns immediately)
    GET  /health           — liveness

The Django backend calls POST /runs with a JSON payload; we schedule the
graph in the background. Events stream via Redis pub/sub to the Django
Channels consumer, then to the SPA WebSocket. Final results are POSTed back
to Django via /api/v1/agent-runs/internal/* callbacks.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal

# Load .env from repo root so OPENROUTER_API_KEY etc are available to litellm
try:
    from dotenv import load_dotenv

    _repo_env = Path(__file__).resolve().parent.parent / ".env"
    if _repo_env.exists():
        load_dotenv(_repo_env)
except ImportError:
    pass

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

from .config import get_settings
from .event_bus import lifespan_bus
from .graphs.content_graph import run_content_graph
from .graphs.curator_graph import run_curator_graph
from .tools.db import close_pool

log = logging.getLogger(__name__)


class RunRequest(BaseModel):
    run_id: str
    workspace_id: str
    graph: Literal["content", "curation", "analysis", "edit"] = "content"
    input: dict[str, Any] = Field(default_factory=dict)


class RunResponse(BaseModel):
    run_id: str
    accepted: bool = True


@asynccontextmanager
async def lifespan(_app: FastAPI):
    async with lifespan_bus():
        try:
            yield
        finally:
            await close_pool()


app = FastAPI(title="helix — agent service", version="0.1.0", lifespan=lifespan)


def _require_internal_auth(authorization: str = Header(default="")) -> None:
    expected = get_settings().agent_service_internal_token
    if not authorization.startswith("Bearer ") or authorization.split(" ", 1)[1] != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "helix-agents"}


@app.post("/runs", response_model=RunResponse)
async def create_run(
    req: RunRequest,
    background: BackgroundTasks,
    _: None = Depends(_require_internal_auth),
) -> RunResponse:
    log.info("Accepted run %s (graph=%s)", req.run_id, req.graph)

    if req.graph == "content":
        initial = {
            "run_id": req.run_id,
            "workspace_id": req.workspace_id,
            "brand_id": req.input.get("brand_id", ""),
            "post_id": req.input.get("post_id", ""),
            "brief": req.input.get("brief", ""),
            "goals": req.input.get("goals", []),
            "tone_hints": req.input.get("tone_hints", []),
            "target_platforms": req.input.get("target_platforms", ["x"]),
            "pinned_reference_ids": req.input.get("pinned_reference_ids", []),
            "variants": [],
        }
        background.add_task(_safe_run, run_content_graph, initial, "content")
        return RunResponse(run_id=req.run_id)

    if req.graph == "curation":
        initial = {
            "run_id": req.run_id,
            "workspace_id": req.workspace_id,
            "brand_id": req.input.get("brand_id", ""),
        }
        background.add_task(_safe_run, run_curator_graph, initial, "curation")
        return RunResponse(run_id=req.run_id)

    raise HTTPException(status_code=400, detail=f"graph '{req.graph}' not implemented yet")


async def _safe_run(coro_fn, initial: dict[str, Any], label: str) -> None:
    try:
        await coro_fn(initial)
    except Exception as exc:  # noqa: BLE001
        log.exception("%s graph run failed: %s", label, exc)


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run("agents.main:app", host="0.0.0.0", port=8001, reload=True)
