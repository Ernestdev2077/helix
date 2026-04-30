"""WebSocket consumer that relays agent run events to the client.

Flow:
    Client opens WS to /ws/agent-runs/<run_id>/
    We join a channel group named ``agent_run_<run_id>``. A Redis listener
    (either a Celery task or a background thread) translates pub/sub messages
    from the agent service into ``group_send`` calls.

For now, we subscribe directly to Redis inside the consumer — simple and
good enough for MVP scale.
"""

from __future__ import annotations

import asyncio
import json
import logging

import redis.asyncio as aioredis
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.conf import settings

from .models import AgentEvent, AgentRun

log = logging.getLogger(__name__)


class AgentRunConsumer(AsyncJsonWebsocketConsumer):
    """Stream AgentRun events to a subscribed client."""

    async def connect(self) -> None:
        self.run_id = self.scope["url_route"]["kwargs"]["run_id"]
        self.user = self.scope.get("user")

        if self.user is None or not self.user.is_authenticated:
            await self.close(code=4401)
            return

        authorized = await self._user_can_view_run()
        if not authorized:
            await self.close(code=4403)
            return

        await self.accept()

        # Replay existing events so late joiners get full context
        replay = await self._recent_events()
        for event in replay:
            await self.send_json({"type": "replay", **event})

        self._stop = asyncio.Event()
        self._listener_task = asyncio.create_task(self._listen_redis())

    async def disconnect(self, code: int) -> None:  # noqa: ARG002
        stop = getattr(self, "_stop", None)
        if stop is not None:
            stop.set()
        task = getattr(self, "_listener_task", None)
        if task is not None:
            task.cancel()

    async def receive_json(self, content, **kwargs) -> None:  # noqa: ARG002
        pass

    async def _listen_redis(self) -> None:
        url = settings.AGENT_STREAM_REDIS_URL
        channel_name = f"agent-run:{self.run_id}"
        try:
            client = aioredis.from_url(url, decode_responses=True)
            pubsub = client.pubsub()
            await pubsub.subscribe(channel_name)
            while not self._stop.is_set():
                msg = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )
                if msg is None:
                    continue
                try:
                    data = json.loads(msg["data"])
                except (ValueError, TypeError):
                    continue
                await self.send_json({"type": "event", **data})
        except asyncio.CancelledError:
            pass
        except Exception as exc:  # noqa: BLE001
            log.warning("Agent run pubsub error for %s: %s", self.run_id, exc)
            await self.send_json({"type": "error", "message": "stream_error"})

    async def _user_can_view_run(self) -> bool:
        from channels.db import database_sync_to_async

        @database_sync_to_async
        def _check() -> bool:
            try:
                run = AgentRun.objects.select_related("workspace").get(id=self.run_id)
            except AgentRun.DoesNotExist:
                return False
            return run.workspace.memberships.filter(user=self.user).exists()

        return await _check()

    async def _recent_events(self) -> list[dict]:
        from channels.db import database_sync_to_async

        @database_sync_to_async
        def _fetch() -> list[dict]:
            events = AgentEvent.objects.filter(run_id=self.run_id).order_by("sequence")[:500]
            return [
                {
                    "sequence": e.sequence,
                    "kind": e.kind,
                    "node_name": e.node_name,
                    "message": e.message,
                    "data": e.data,
                    "created_at": e.created_at.isoformat(),
                }
                for e in events
            ]

        return await _fetch()
