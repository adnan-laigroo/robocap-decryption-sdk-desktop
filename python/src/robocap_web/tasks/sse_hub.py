from __future__ import annotations

import asyncio
import json
from collections import deque
from typing import Any, AsyncIterator


class SseHub:
    def __init__(self, buffer_size: int = 50) -> None:
        self._buffer_size = buffer_size
        self._buffers: dict[str, deque[dict[str, Any]]] = {}
        self._subscribers: dict[str, list[asyncio.Queue]] = {}

    def emit(self, task_id: str, event: str, data: dict[str, Any]) -> None:
        payload = {"event": event, "data": data}
        buf = self._buffers.setdefault(task_id, deque(maxlen=self._buffer_size or None))
        if self._buffer_size > 0:
            buf.append(payload)
        for queue in self._subscribers.get(task_id, []):
            queue.put_nowait(payload)

    def recent_events(self, task_id: str) -> list[dict[str, Any]]:
        return list(self._buffers.get(task_id, []))

    async def subscribe(self, task_id: str) -> AsyncIterator[dict[str, Any]]:
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.setdefault(task_id, []).append(queue)
        try:
            while True:
                item = await queue.get()
                yield item
        finally:
            subs = self._subscribers.get(task_id, [])
            if queue in subs:
                subs.remove(queue)

    @staticmethod
    def format_sse(payload: dict[str, Any]) -> str:
        event = payload.get("event", "message")
        data = json.dumps(payload.get("data", {}), ensure_ascii=False)
        return f"event: {event}\ndata: {data}\n\n"
