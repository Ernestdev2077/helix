"""Internal endpoints — called by the agent service over HTTP, not by SPA users.

Auth via shared bearer token (settings.AGENT_SERVICE_INTERNAL_TOKEN). Avoids
needing a real user session for the agent service to write back results.
"""

from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response

from apps.content.models import Post, PostVariant, Reference, StyleRule

from .models import AgentEvent, AgentRun

log = logging.getLogger(__name__)


def _check_internal_auth(request: Request) -> bool:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return False
    return auth.split(" ", 1)[1] == settings.AGENT_SERVICE_INTERNAL_TOKEN


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
@transaction.atomic
def content_completed(request: Request) -> Response:
    """Agent service calls this when a content graph run finishes.

    Payload:
    {
      "run_id": "<uuid>",
      "post_id": "<uuid>",
      "variants": [
        {"platform": "x", "label": "A", "content": "...",
         "inspired_by_reference_ids": [...], "inspired_by_rule_ids": [...]}
      ],
      "tokens_in": 0, "tokens_out": 0, "cost_usd": 0,
      "critic_notes": [...]
    }
    """
    if not _check_internal_auth(request):
        return Response({"error": "unauthorized"}, status=401)

    payload: dict[str, Any] = request.data
    run_id = payload.get("run_id")
    post_id = payload.get("post_id")

    try:
        run = AgentRun.objects.select_related("post").get(id=run_id)
    except AgentRun.DoesNotExist:
        return Response({"error": "run_not_found"}, status=404)

    try:
        post = Post.objects.get(id=post_id, workspace=run.workspace)
    except Post.DoesNotExist:
        return Response({"error": "post_not_found"}, status=404)

    PostVariant.objects.filter(post=post).delete()

    created_variants = []
    for v in payload.get("variants", []):
        variant = PostVariant.objects.create(
            post=post,
            platform=v["platform"],
            label=v.get("label", "A"),
            content=v.get("content", ""),
            critic_notes=v.get("critic_notes", []),
        )
        ref_ids = v.get("inspired_by_reference_ids", [])
        rule_ids = v.get("inspired_by_rule_ids", [])
        if ref_ids:
            variant.inspired_by_references.set(
                Reference.objects.filter(id__in=ref_ids, workspace=run.workspace)
            )
        if rule_ids:
            variant.inspired_by_style_rules.set(
                StyleRule.objects.filter(id__in=rule_ids, workspace=run.workspace)
            )
        created_variants.append(str(variant.id))

    post.status = Post.Status.REVIEW
    post.save(update_fields=["status", "updated_at"])

    run.status = AgentRun.Status.COMPLETED
    run.finished_at = timezone.now()
    run.output_payload = {
        "variant_ids": created_variants,
        "critic_notes": payload.get("critic_notes", []),
    }
    run.total_tokens_in = payload.get("tokens_in", 0)
    run.total_tokens_out = payload.get("tokens_out", 0)
    run.save(
        update_fields=[
            "status",
            "finished_at",
            "output_payload",
            "total_tokens_in",
            "total_tokens_out",
            "updated_at",
        ]
    )

    return Response({"ok": True, "variant_count": len(created_variants)})


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
@transaction.atomic
def emit_event(request: Request) -> Response:
    """Optional: persist a single AgentEvent to DB (so it shows in replay).

    Most events go via Redis pub/sub for live streaming; this endpoint is for
    important ones we want to keep in the timeline forever (e.g. node finished,
    critic flagged). Best-effort — if writes fail, we still keep streaming.
    """
    if not _check_internal_auth(request):
        return Response({"error": "unauthorized"}, status=401)

    payload: dict[str, Any] = request.data
    try:
        run = AgentRun.objects.get(id=payload["run_id"])
    except (AgentRun.DoesNotExist, KeyError):
        return Response({"error": "run_not_found"}, status=404)

    AgentEvent.objects.create(
        run=run,
        sequence=payload["sequence"],
        kind=payload.get("kind", "info"),
        node_name=payload.get("node_name", ""),
        message=payload.get("message", ""),
        data=payload.get("data", {}),
        tokens_in=payload.get("tokens_in", 0),
        tokens_out=payload.get("tokens_out", 0),
        duration_ms=payload.get("duration_ms", 0),
    )
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
@transaction.atomic
def curation_completed(request: Request) -> Response:
    """Agent service calls this when Curator finishes proposing rules.

    Payload:
    {
      "run_id": "<uuid>",
      "workspace_id": "<uuid>",
      "brand_id": "<uuid>",
      "proposed_rules": [
        {"scope": "global", "platform": "", "rule_text": "...",
         "rationale": "...", "confidence": 0.82,
         "evidence_reference_ids": [...]}
      ]
    }
    """
    if not _check_internal_auth(request):
        return Response({"error": "unauthorized"}, status=401)

    payload: dict[str, Any] = request.data
    try:
        run = AgentRun.objects.get(id=payload["run_id"])
    except (AgentRun.DoesNotExist, KeyError):
        return Response({"error": "run_not_found"}, status=404)

    created = 0
    for r in payload.get("proposed_rules", []):
        rule = StyleRule.objects.create(
            workspace=run.workspace,
            brand_id=payload["brand_id"],
            scope=r.get("scope", "global"),
            platform=r.get("platform", ""),
            rule_text=r["rule_text"][:400],
            rationale=r.get("rationale", ""),
            confidence=r.get("confidence", 0.5),
            status=StyleRule.Status.PROPOSED,
        )
        ref_ids = r.get("evidence_reference_ids", [])
        if ref_ids:
            rule.evidence_references.set(
                Reference.objects.filter(id__in=ref_ids, workspace=run.workspace)
            )
        created += 1

    run.status = AgentRun.Status.COMPLETED
    run.finished_at = timezone.now()
    run.output_payload = {"proposed_rule_count": created}
    run.save(update_fields=["status", "finished_at", "output_payload", "updated_at"])

    return Response({"ok": True, "proposed_rule_count": created})
