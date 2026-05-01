"""Service layer for kicking off agent runs against the FastAPI agent service."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import httpx
from django.conf import settings
from django.utils import timezone

from .models import AgentRun

if TYPE_CHECKING:  # pragma: no cover
    from apps.accounts.models import User
    from apps.brands.models import Brand
    from apps.content.models import Post, PostVariant, Reference

log = logging.getLogger(__name__)


def _post_to_agent_service(payload: dict) -> bool:
    headers = {"Authorization": f"Bearer {settings.AGENT_SERVICE_INTERNAL_TOKEN}"}
    try:
        response = httpx.post(
            f"{settings.AGENT_SERVICE_URL}/runs",
            json=payload,
            headers=headers,
            timeout=10.0,
        )
        response.raise_for_status()
        return True
    except httpx.HTTPError as exc:
        log.warning("Agent service unavailable: %s", exc)
        return False


def start_content_generation(*, post: "Post", user: "User") -> AgentRun:
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
        "input": {
            "post_id": str(post.id),
            "brand_id": str(post.brand_id),
            "brief": post.brief,
            "goals": list(post.goals),
            "tone_hints": list(post.tone_hints),
            "target_platforms": list(post.target_platforms),
            "pinned_reference_ids": [str(x) for x in post.pinned_reference_ids],
        },
    }
    if _post_to_agent_service(payload):
        run.status = AgentRun.Status.RUNNING
        run.started_at = timezone.now()
        run.save(update_fields=["status", "started_at", "updated_at"])
    return run


def start_curation(*, brand: "Brand", user: "User") -> AgentRun:
    run = AgentRun.objects.create(
        workspace=brand.workspace,
        kind=AgentRun.Kind.CURATION,
        status=AgentRun.Status.QUEUED,
        triggered_by=user,
        input_payload={"brand_id": str(brand.id)},
    )

    payload = {
        "run_id": str(run.id),
        "workspace_id": str(brand.workspace_id),
        "graph": "curation",
        "input": {"brand_id": str(brand.id)},
    }
    if _post_to_agent_service(payload):
        run.status = AgentRun.Status.RUNNING
        run.started_at = timezone.now()
        run.save(update_fields=["status", "started_at", "updated_at"])
    return run


def start_ab_variation(*, variant: "PostVariant", user: "User") -> AgentRun:
    """Refine a starred variant — generate N reframings via the ab_variation graph."""
    post = variant.post
    run = AgentRun.objects.create(
        workspace=post.workspace,
        kind=AgentRun.Kind.AB_VARIATION,
        status=AgentRun.Status.QUEUED,
        post=post,
        triggered_by=user,
        input_payload={
            "source_variant_id": str(variant.id),
            "post_id": str(post.id),
        },
    )

    payload = {
        "run_id": str(run.id),
        "workspace_id": str(post.workspace_id),
        "graph": "ab_variation",
        "input": {"source_variant_id": str(variant.id)},
    }
    if _post_to_agent_service(payload):
        run.status = AgentRun.Status.RUNNING
        run.started_at = timezone.now()
        run.save(update_fields=["status", "started_at", "updated_at"])
    return run


def start_reference_dna(*, reference: "Reference", user: "User | None") -> AgentRun:
    """Extract writing-DNA from a reference. Auto-fired on Reference creation."""
    run = AgentRun.objects.create(
        workspace=reference.workspace,
        kind=AgentRun.Kind.REFERENCE_DNA,
        status=AgentRun.Status.QUEUED,
        triggered_by=user,
        input_payload={
            "reference_id": str(reference.id),
            "brand_id": str(reference.brand_id),
        },
    )

    payload = {
        "run_id": str(run.id),
        "workspace_id": str(reference.workspace_id),
        "graph": "reference_dna",
        "input": {
            "reference_id": str(reference.id),
            "brand_id": str(reference.brand_id),
            "reference_text": reference.raw_text,
            "reference_platform": reference.platform,
        },
    }
    if _post_to_agent_service(payload):
        run.status = AgentRun.Status.RUNNING
        run.started_at = timezone.now()
        run.save(update_fields=["status", "started_at", "updated_at"])
    return run
