"""Service layer for kicking off agent runs against the FastAPI agent service.

We POST to the agent service, which streams events back via Redis pub/sub on
channel ``agent-run:<run_id>``. The Django Channels consumer bridges that
stream to the client's WebSocket.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import httpx
from django.conf import settings
from django.utils import timezone

from .models import AgentRun

if TYPE_CHECKING:  # pragma: no cover
    from apps.accounts.models import User
    from apps.content.models import Post

log = logging.getLogger(__name__)


def start_content_generation(*, post: "Post", user: "User") -> AgentRun:
    """Create an AgentRun record and ask the agent service to begin execution.

    We return immediately with the AgentRun; events stream over WebSocket.
    """
    run = AgentRun.objects.create(
        workspace=post.workspace,
        kind=AgentRun.Kind.CONTENT,
        status=AgentRun.Status.QUEUED,
        post=post,
        triggered_by=user,
        input_payload={
            "post_id": str(post.id),
            "brand_id": str(post.brand_id),
            "brief": post.brief,
            "goals": list(post.goals),
            "tone_hints": list(post.tone_hints),
            "target_platforms": list(post.target_platforms),
            "pinned_reference_ids": [str(x) for x in post.pinned_reference_ids],
        },
    )

    payload = {
        "run_id": str(run.id),
        "workspace_id": str(post.workspace_id),
        "graph": "content",
        "input": run.input_payload,
    }
    headers = {"Authorization": f"Bearer {settings.AGENT_SERVICE_INTERNAL_TOKEN}"}

    try:
        response = httpx.post(
            f"{settings.AGENT_SERVICE_URL}/runs",
            json=payload,
            headers=headers,
            timeout=10.0,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        log.warning("Agent service unavailable, run will stay queued: %s", exc)
        # Stays in QUEUED — a sweeper task can retry, or user can re-kick it.
        return run

    run.status = AgentRun.Status.RUNNING
    run.started_at = timezone.now()
    run.save(update_fields=["status", "started_at", "updated_at"])
    return run
