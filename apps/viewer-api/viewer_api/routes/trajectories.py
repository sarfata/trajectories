"""Trajectory CRUD routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from trajectory_schema import (
    TagCreate,
    Trajectory,
    TrajectoryCreate,
    TrajectorySummary,
)

from ..db import (
    add_tag,
    get_trajectory,
    insert_trajectory,
    list_trajectories,
    remove_tag,
)
from ..sse.hub import hub

router = APIRouter(prefix="/api", tags=["trajectories"])


@router.post(
    "/trajectories",
    response_model=TrajectorySummary,
    status_code=201,
    summary="Ingest a single trajectory",
    description="Accept a trajectory in compact form, store it, and publish an SSE event.",
)
async def create_trajectory(traj: TrajectoryCreate) -> TrajectorySummary:
    summary = await insert_trajectory(traj)
    await hub.publish("trajectory.created", {"id": summary.id, "summary": summary.model_dump()})
    return summary


@router.get(
    "/trajectories",
    response_model=list[TrajectorySummary],
    summary="List trajectories",
    description="Paginated list of trajectories, newest first. Use cursor for pagination.",
)
async def list_trajectories_route(
    limit: int = Query(default=50, ge=1, le=200),
    cursor: int | None = Query(default=None, description="started_at value to paginate from"),
    run_id: str | None = Query(default=None),
) -> list[TrajectorySummary]:
    return await list_trajectories(limit=limit, cursor=cursor, run_id=run_id)


@router.get(
    "/trajectories/{traj_id}",
    response_model=Trajectory,
    summary="Get trajectory detail",
    description="Full trajectory including events, scores, messages, and tags.",
)
async def get_trajectory_route(traj_id: str) -> Trajectory:
    t = await get_trajectory(traj_id)
    if not t:
        raise HTTPException(status_code=404, detail="Trajectory not found")
    return t


@router.post(
    "/trajectories/{traj_id}/tags",
    status_code=201,
    summary="Add a tag to a trajectory",
)
async def add_tag_route(traj_id: str, body: TagCreate) -> dict[str, str]:
    t = await get_trajectory(traj_id)
    if not t:
        raise HTTPException(status_code=404, detail="Trajectory not found")
    added = await add_tag(traj_id, body.tag)
    if not added:
        raise HTTPException(status_code=409, detail="Tag already exists")
    await hub.publish("trajectory.tagged", {"id": traj_id, "tag": body.tag})
    return {"status": "ok", "tag": body.tag}


@router.delete(
    "/trajectories/{traj_id}/tags/{tag}",
    summary="Remove a tag from a trajectory",
)
async def remove_tag_route(traj_id: str, tag: str) -> dict[str, str]:
    removed = await remove_tag(traj_id, tag)
    if not removed:
        raise HTTPException(status_code=404, detail="Tag not found")
    await hub.publish("trajectory.untagged", {"id": traj_id, "tag": tag})
    return {"status": "ok"}
