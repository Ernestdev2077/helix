"""Thin client to call Django internal endpoints from the agent service.

Used to:
- Load context for a run (brand voice, KB chunks, references, active rules)
- Persist generated variants and curated style rules back

We use a Django service token (settings.AGENT_SERVICE_INTERNAL_TOKEN) to
authenticate; no per-user JWT needed because the agent service is trusted.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

log = logging.getLogger(__name__)


def _backend_url() -> str:
    return os.getenv("HELIX_BACKEND_URL", "http://127.0.0.1:8088")


def _headers() -> dict[str, str]:
    token = os.getenv("AGENT_SERVICE_INTERNAL_TOKEN", "dev-internal-token-local-only")
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


async def post_internal(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    url = f"{_backend_url()}{path}"
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            r = await client.post(url, json=payload, headers=_headers())
            if r.status_code >= 400:
                log.warning("Internal POST %s → %s: %s", path, r.status_code, r.text[:300])
            return r.json() if r.content else {}
        except httpx.HTTPError as exc:
            log.warning("Internal POST %s failed: %s", path, exc)
            return {"error": str(exc)}


async def report_content_completed(payload: dict[str, Any]) -> dict[str, Any]:
    return await post_internal("/api/v1/agent-runs/internal/content-completed/", payload)


async def report_curation_completed(payload: dict[str, Any]) -> dict[str, Any]:
    return await post_internal("/api/v1/agent-runs/internal/curation-completed/", payload)
