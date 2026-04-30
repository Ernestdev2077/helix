from __future__ import annotations

from django.urls import path

from .consumers import AgentRunConsumer

websocket_urlpatterns = [
    path("ws/agent-runs/<uuid:run_id>/", AgentRunConsumer.as_asgi()),
]
