"""Workspace resolution middleware.

Resolves the "active workspace" for the current request using either:
1. ``X-Workspace`` header (slug or UUID) — typical for SPA clients
2. ``?workspace=<slug>`` query param — for embeddable links
3. User's default workspace (first membership, ordered by -created_at) — fallback

The resolved workspace is attached to ``request.workspace`` and ``request.membership``.
Views and viewsets use ``apps.workspaces.permissions`` to enforce access.

We do not 404 here — unauthenticated requests or requests to endpoints that
don't need a workspace simply get ``None`` values.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING
from uuid import UUID

from django.http import HttpRequest, HttpResponse

if TYPE_CHECKING:  # pragma: no cover
    from .models import Membership, Workspace


class WorkspaceContextMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request.workspace = None  # type: ignore[attr-defined]
        request.membership = None  # type: ignore[attr-defined]

        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return self.get_response(request)

        identifier = request.headers.get("X-Workspace") or request.GET.get("workspace")

        from .models import Membership  # imported here to avoid AppRegistry errors

        qs = Membership.objects.select_related("workspace").filter(user=user)

        membership: Membership | None = None
        if identifier:
            membership = self._resolve_membership(qs, identifier)
        if membership is None:
            membership = qs.order_by("-created_at").first()

        if membership is not None:
            request.membership = membership  # type: ignore[attr-defined]
            request.workspace = membership.workspace  # type: ignore[attr-defined]

        return self.get_response(request)

    @staticmethod
    def _resolve_membership(qs, identifier: str) -> "Membership | None":
        try:
            uuid_val = UUID(identifier)
            return qs.filter(workspace_id=uuid_val).first()
        except (ValueError, TypeError):
            return qs.filter(workspace__slug=identifier).first()
