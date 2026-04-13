"""SSE event stream route."""

from __future__ import annotations

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from ..sse.hub import hub

router = APIRouter(tags=["events"])


@router.get(
    "/api/events",
    summary="SSE event stream",
    description="Server-sent events for real-time updates. Events: trajectory.created, trajectory.updated, trajectory.tagged, trajectory.untagged, run.created",
)
async def sse_stream():
    async def generate():
        async for msg in hub.subscribe():
            yield msg

    return EventSourceResponse(generate())
