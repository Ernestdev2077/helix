from __future__ import annotations

import logging
from datetime import timedelta
from urllib.parse import urlencode

import httpx
from django.conf import settings
from django.http import HttpResponseRedirect
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.content.models import Platform
from apps.workspaces.permissions import HasActiveWorkspace, IsWorkspaceEditor

from . import oauth
from .models import PlatformAccount, Publication
from .serializers import PlatformAccountSerializer, PublicationSerializer

log = logging.getLogger(__name__)


class PlatformAccountViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only list of connected accounts. Creation happens via OAuth flow."""

    serializer_class = PlatformAccountSerializer
    permission_classes = [IsWorkspaceEditor]
    lookup_field = "id"

    def get_queryset(self):
        workspace = getattr(self.request, "workspace", None)
        if workspace is None:
            return PlatformAccount.objects.none()
        return PlatformAccount.objects.filter(workspace=workspace)


class PublicationViewSet(viewsets.ModelViewSet):
    serializer_class = PublicationSerializer
    permission_classes = [IsWorkspaceEditor]
    lookup_field = "id"

    def get_queryset(self):
        workspace = getattr(self.request, "workspace", None)
        if workspace is None:
            return Publication.objects.none()
        return Publication.objects.filter(workspace=workspace).select_related(
            "variant", "platform_account"
        )

    def perform_create(self, serializer) -> None:
        serializer.save(workspace=self.request.workspace)


# ---------------------------------------------------------------------------
# OAuth status + flow endpoints
# ---------------------------------------------------------------------------


@api_view(["GET"])
@permission_classes([HasActiveWorkspace])
def oauth_status(request) -> Response:
    """Per-platform configuration + connection status for the active workspace."""
    workspace = request.workspace
    accounts = {
        a.platform: a
        for a in PlatformAccount.objects.filter(
            workspace=workspace, status=PlatformAccount.Status.ACTIVE
        )
    }

    def _platform_status(platform: str, configured: bool) -> dict:
        acc = accounts.get(platform)
        return {
            "configured": configured,
            "connected": acc is not None,
            "handle": acc.handle if acc else "",
            "display_name": acc.display_name if acc else "",
        }

    return Response({
        "x": _platform_status(Platform.X, bool(settings.X_CLIENT_ID)),
        "reddit": _platform_status(Platform.REDDIT, bool(settings.REDDIT_CLIENT_ID)),
        "linkedin": _platform_status(Platform.LINKEDIN, bool(settings.LINKEDIN_CLIENT_ID)),
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def x_oauth_start(request):
    """Redirect the user to X's authorization screen.

    PKCE state is stored in the Django session because we need to validate it
    on the redirect-back. Browsers will send the session cookie on the
    redirect-back from X to our /callback endpoint.
    """
    if not settings.X_CLIENT_ID:
        return Response({"error": "x_oauth_not_configured"}, status=503)

    workspace = getattr(request, "workspace", None)
    if workspace is None:
        return Response({"error": "active_workspace_required"}, status=400)

    flow = oauth.make_pkce()
    request.session["x_oauth"] = flow.to_session_dict()
    request.session["x_oauth_workspace_id"] = str(workspace.id)
    request.session.modified = True

    redirect_uri = settings.X_REDIRECT_URI or _default_x_redirect_uri(request)
    auth_url = oauth.build_x_auth_url(
        client_id=settings.X_CLIENT_ID,
        redirect_uri=redirect_uri,
        flow=flow,
    )
    return HttpResponseRedirect(auth_url)


@api_view(["GET"])
@permission_classes([AllowAny])  # X redirects browser back; user is already authed via session
def x_oauth_callback(request):
    code = request.GET.get("code")
    state = request.GET.get("state")
    saved = request.session.get("x_oauth") or {}
    workspace_id = request.session.get("x_oauth_workspace_id")

    failure_url = _onboarding_url(step=2, params={"connected": "x", "error": "1"})

    if not code or not state or not saved or saved.get("state") != state or not workspace_id:
        return HttpResponseRedirect(failure_url)

    redirect_uri = settings.X_REDIRECT_URI or _default_x_redirect_uri(request)
    try:
        token_data = oauth.exchange_x_code(
            client_id=settings.X_CLIENT_ID,
            client_secret=settings.X_CLIENT_SECRET,
            redirect_uri=redirect_uri,
            code=code,
            code_verifier=saved["code_verifier"],
        )
    except httpx.HTTPError as exc:
        log.warning("X token exchange failed: %s", exc)
        return HttpResponseRedirect(failure_url)

    access_token = token_data.get("access_token", "")
    refresh_token = token_data.get("refresh_token", "")
    expires_in = token_data.get("expires_in", 0)

    try:
        me = oauth.fetch_x_user_me(access_token=access_token)
    except httpx.HTTPError as exc:
        log.warning("X /users/me failed: %s", exc)
        me = {}

    PlatformAccount.objects.update_or_create(
        workspace_id=workspace_id,
        platform=Platform.X,
        external_id=me.get("id", "") or saved["state"],  # fallback so unique_together is happy
        defaults={
            "handle": me.get("username", ""),
            "display_name": me.get("name", ""),
            "avatar_url": me.get("profile_image_url", ""),
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_expires_at": timezone.now() + timedelta(seconds=int(expires_in or 0))
            if expires_in else None,
            "scopes": (token_data.get("scope") or "").split(),
            "status": PlatformAccount.Status.ACTIVE,
            "connected_by": request.user if request.user.is_authenticated else None,
        },
    )

    request.session.pop("x_oauth", None)
    request.session.pop("x_oauth_workspace_id", None)

    return HttpResponseRedirect(_onboarding_url(step=2, params={"connected": "x"}))


def _default_x_redirect_uri(request) -> str:
    """Build a redirect URI when X_REDIRECT_URI is not set in env."""
    return request.build_absolute_uri("/api/v1/auth/oauth/x/callback/")


def _onboarding_url(*, step: int, params: dict | None = None) -> str:
    base = settings.FRONTEND_URL.rstrip("/")
    qs = {"step": step, **(params or {})}
    return f"{base}/onboarding?{urlencode(qs)}"
