"""In-process SSE fan-out using asyncio.Queue."""

from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator


class SSEEvent:
    """Structured SSE event for sse-starlette."""

    __slots__ = ("event", "data")

    def __init__(self, event: str, data: dict[str, Any]) -> None:
        self.event = event
        self.data = json.dumps(data)


class SSEHub:
    """Manages SSE client connections and broadcasts events."""

    def __init__(self) -> None:
        self._queues: set[asyncio.Queue[SSEEvent | None]] = set()

    async def publish(self, event_type: str, data: dict[str, Any]) -> None:
        """Push an event to all connected clients."""
        evt = SSEEvent(event_type, data)
        dead: list[asyncio.Queue[SSEEvent | None]] = []
        for q in self._queues:
            try:
                q.put_nowait(evt)
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            self._queues.discard(q)

    async def subscribe(self) -> AsyncIterator[dict[str, str]]:
        """Yield dicts for EventSourceResponse."""
        q: asyncio.Queue[SSEEvent | None] = asyncio.Queue(maxsize=256)
        self._queues.add(q)
        try:
            while True:
                msg = await q.get()
                if msg is None:
                    break
                yield {"event": msg.event, "data": msg.data}
        finally:
            self._queues.discard(q)

    @property
    def client_count(self) -> int:
        return len(self._queues)


hub = SSEHub()
