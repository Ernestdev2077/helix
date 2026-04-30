"""FastAPI entrypoint for the agent service.

Endpoints:
    POST /runs             — kick off a graph run (async)
    GET  /health           — liveness

The Django backend calls POST /runs with a JSON payload; we schedule the
graph in the background and return immediately. Events stream over Redis
pub/sub (see ``event_bus.py``) to the Django Channels consumer, which
forwards them to the client's WebSocket.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, Literal

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from .config import get_settings
from .event_bus import lifespan_bus
from .graphs.content_graph import run_content_graph

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
        yield


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
            "brief": req.input.get("brief", ""),
            "goals": req.input.get("goals", []),
            "tone_hints": req.input.get("tone_hints", []),
            "target_platforms": req.input.get("target_platforms", ["x"]),
            "pinned_reference_ids": req.input.get("pinned_reference_ids", []),
            "variants": [],
        }
        background.add_task(_run_content, initial)
        return RunResponse(run_id=req.run_id)

    raise HTTPException(status_code=400, detail=f"graph '{req.graph}' not implemented yet")


async def _run_content(initial: dict[str, Any]) -> None:
    try:
        await run_content_graph(initial)  # type: ignore[arg-type]
    except Exception as exc:  # noqa: BLE001
        log.exception("Content graph run failed: %s", exc)


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run("agents.main:app", host="0.0.0.0", port=8001, reload=True)
