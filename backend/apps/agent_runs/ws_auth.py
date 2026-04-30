"""JWT auth middleware for Django Channels.

Reads `?token=<jwt>` from the WebSocket query string and resolves the user
before the consumer's connect() runs. Browsers can't set Authorization
headers on WebSocket handshakes, so query-param is the standard workaround.
"""

from __future__ import annotations

from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser


@database_sync_to_async
def _get_user_from_token(token: str):
    if not token:
        return AnonymousUser()
    try:
        from rest_framework_simplejwt.authentication import JWTAuthentication
        from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
    except ImportError:
        return AnonymousUser()

    try:
        validated = JWTAuthentication().get_validated_token(token)
        user = JWTAuthentication().get_user(validated)
        return user
    except (InvalidToken, TokenError, Exception):  # noqa: BLE001
        return AnonymousUser()


class JWTAuthMiddleware:
    """Channels middleware: reads ?token=… and sets scope['user']."""

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        if scope.get("user") is None or scope["user"].is_anonymous:
            query_string = scope.get("query_string", b"").decode()
            params = parse_qs(query_string)
            token = (params.get("token") or [""])[0]
            if token:
                scope["user"] = await _get_user_from_token(token)
        return await self.inner(scope, receive, send)


def JWTAuthMiddlewareStack(inner):  # noqa: N802 — match Channels naming
    return JWTAuthMiddleware(inner)
