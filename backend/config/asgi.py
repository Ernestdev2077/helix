"""ASGI entrypoint — supports HTTP + WebSocket via Django Channels."""

from __future__ import annotations

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

django_asgi_app = get_asgi_application()

from apps.agent_runs.routing import websocket_urlpatterns  # noqa: E402
from apps.agent_runs.ws_auth import JWTAuthMiddlewareStack  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        # JWT first (reads ?token= from query string), then session fallback,
        # then origin validation for safety.
        "websocket": AllowedHostsOriginValidator(
            JWTAuthMiddlewareStack(
                AuthMiddlewareStack(URLRouter(websocket_urlpatterns))
            )
        ),
    }
)
