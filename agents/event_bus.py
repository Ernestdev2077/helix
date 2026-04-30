"""Redis pub/sub event bus — streams agent run events to Django consumers.

We publish JSON messages to ``agent-run:<run_id>`` channels. The Django
WebSocket consumer subscribes and forwards to the connected client.

Events follow the ``AgentEvent`` shape used by the backend so the client
can treat live stream and replay events identically.
"""

from __future__ import annotations

import json
import logging
import time
from contextlib import asynccontextmanager
from typing import Any

import redis.asyncio as aioredis

from .config import get_settings

log = logging.getLogger(__name__)


class EventBus:
    """Thin Redis pub/sub wrapper specialized for agent-run event streaming."""

    def __init__(self) -> None:
        self._client: aioredis.Redis | None = None

    async def connect(self) -> None:
        if self._client is None:
            settings = get_settings()
            self._client = aioredis.from_url(
                settings.agent_stream_redis_url, decode_responses=True
            )

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def publish(
        self,
        *,
        run_id: str,
        sequence: int,
        kind: str,
        node_name: str = "",
        message: str = "",
        data: dict[str, Any] | None = None,
        tokens_in: int = 0,
        tokens_out: int = 0,
        duration_ms: int = 0,
    ) -> None:
        if self._client is None:
            await self.connect()
        payload = {
            "run_id": run_id,
            "sequence": sequence,
            "kind": kind,
            "node_name": node_name,
            "message": message,
            "data": data or {},
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "duration_ms": duration_ms,
            "emitted_at": time.time(),
        }
        channel = f"agent-run:{run_id}"
        assert self._client is not None
        try:
            await self._client.publish(channel, json.dumps(payload))
        except Exception as exc:  # noqa: BLE001
            log.warning("Failed to publish event for run %s: %s", run_id, exc)


_bus: EventBus | None = None


async def get_bus() -> EventBus:
    global _bus
    if _bus is None:
        _bus = EventBus()
        await _bus.connect()
    return _bus


@asynccontextmanager
async def lifespan_bus():
    bus = EventBus()
    await bus.connect()
    global _bus
    _bus = bus
    try:
        yield bus
    finally:
        await bus.close()
        _bus = None
