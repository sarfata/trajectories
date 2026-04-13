"""Run routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from trajectory_schema import RunSummary, TrajectorySummary

from ..db import get_run, list_runs, list_trajectories

router = APIRouter(prefix="/api", tags=["runs"])


@router.get(
    "/runs",
    response_model=list[RunSummary],
    summary="List runs",
    description="List EvalLog-level runs, newest first.",
)
async def list_runs_route(
    limit: int = Query(default=50, ge=1, le=200),
) -> list[RunSummary]:
    rows = await list_runs(limit=limit)
    return [
        RunSummary(
            id=r["id"],
            task=r["task"],
            model=r["model"],
            created_at=r["created_at"],
            status=r["status"],
            sample_count=r["sample_count"],
        )
        for r in rows
    ]


@router.get(
    "/runs/{run_id}",
    summary="Get run detail",
    description="Run summary with sample count and list of trajectories.",
)
async def get_run_route(run_id: str) -> dict:
    r = await get_run(run_id)
    if not r:
        raise HTTPException(status_code=404, detail="Run not found")
    trajectories = await list_trajectories(limit=200, run_id=run_id)
    return {
        "id": r["id"],
        "task": r["task"],
        "model": r["model"],
        "created_at": r["created_at"],
        "status": r["status"],
        "sample_count": r["sample_count"],
        "trajectories": [t.model_dump() for t in trajectories],
    }
