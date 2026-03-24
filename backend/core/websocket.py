import asyncio
import json
import logging
import uuid
from typing import Optional

import redis.asyncio as aioredis
from fastapi import WebSocket

from config import settings

logger = logging.getLogger("coffee_time_saver")

WS_CHANNEL = "ws_events"


class ConnectionManager:
    """
    Manages WebSocket connections and Redis pub/sub for pushing events
    from Celery workers to connected frontend clients.
    """

    def __init__(self):
        self._connections: dict[str, list[WebSocket]] = {}
        self._redis: Optional[aioredis.Redis] = None
        self._pubsub_task: Optional[asyncio.Task] = None

    async def startup(self) -> None:
        self._redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        self._pubsub_task = asyncio.create_task(self._listen())

    async def shutdown(self) -> None:
        if self._pubsub_task:
            self._pubsub_task.cancel()
        if self._redis:
            await self._redis.aclose()

    async def connect(self, websocket: WebSocket, user_id: uuid.UUID) -> None:
        await websocket.accept()
        key = str(user_id)
        self._connections.setdefault(key, []).append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: uuid.UUID) -> None:
        key = str(user_id)
        conns = self._connections.get(key, [])
        if websocket in conns:
            conns.remove(websocket)
        if not conns:
            self._connections.pop(key, None)

    async def broadcast_to_user(self, user_id: uuid.UUID, event: dict) -> None:
        key = str(user_id)
        message = json.dumps(event)
        for ws in list(self._connections.get(key, [])):
            try:
                await ws.send_text(message)
            except Exception:
                self.disconnect(ws, user_id)

    async def broadcast_all(self, event: dict) -> None:
        message = json.dumps(event)
        for user_id_str, conns in list(self._connections.items()):
            for ws in list(conns):
                try:
                    await ws.send_text(message)
                except Exception:
                    self.disconnect(ws, uuid.UUID(user_id_str))

    async def publish(self, user_id: Optional[uuid.UUID], event: dict) -> None:
        """Called by Celery workers via Redis to push events to WebSocket clients.
        Creates a one-shot connection when called from outside the FastAPI process (e.g. Celery)."""
        payload = json.dumps({"user_id": str(user_id) if user_id else None, "event": event})
        if self._redis:
            await self._redis.publish(WS_CHANNEL, payload)
        else:
            # One-shot connection for Celery workers (manager.startup() not called there)
            r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            try:
                await r.publish(WS_CHANNEL, payload)
            finally:
                await r.aclose()

    async def _listen(self) -> None:
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(WS_CHANNEL)
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            try:
                data = json.loads(message["data"])
                event = data["event"]
                user_id_str = data.get("user_id")
                if user_id_str:
                    await self.broadcast_to_user(uuid.UUID(user_id_str), event)
                else:
                    await self.broadcast_all(event)
            except Exception as e:
                logger.error("WebSocket pubsub error: %s", e)


manager = ConnectionManager()
