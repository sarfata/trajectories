"""Meta routes: llms.txt, distinct values for filters."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from ..db import get_distinct_models, get_distinct_tags

router = APIRouter(tags=["meta"])


LLMS_TXT = """# Trajectory Viewer

A researcher-facing tool for browsing coding-model trajectories live during training/eval runs.
Trajectories are single samples from an Inspect AI EvalLog — complete model runs with events, tool calls, scores, and user-added tags.

## Endpoints

- `GET /api/trajectories` — list trajectories (newest first, paginated)
- `GET /api/trajectories/{id}` — full trajectory with events, scores, tags
- `POST /api/trajectories` — ingest a single trajectory (compact JSON)
- `GET /api/runs` — list eval runs
- `GET /api/runs/{id}` — run detail with trajectories
- `POST /api/search` — SQL query against v_trajectories view
- `GET /api/search/columns` — column metadata for autocomplete
- `GET /api/search/examples` — example SQL queries
- `POST /api/trajectories/{id}/tags` — add a tag
- `DELETE /api/trajectories/{id}/tags/{tag}` — remove a tag
- `GET /api/events` — SSE stream for real-time updates
- `GET /openapi.json` — full OpenAPI schema
- `GET /docs` — Swagger UI

## Search

The SQL search box accepts `SELECT` queries against `v_trajectories`. Columns:
id, run_id, task, task_id, model, harness, status, started_at, completed_at,
duration_ms, step_count, tool_call_count, compaction_count, total_tokens,
tool_names, eval_verdict, eval_score, tags, scorers.

Queries are wrapped with `LIMIT 500` and have a 5s timeout.

## SSE Events

- `trajectory.created` — new trajectory ingested
- `trajectory.tagged` / `trajectory.untagged` — tag changes
- `run.created` — new run ingested
"""


@router.get("/llms.txt", response_class=PlainTextResponse, include_in_schema=False)
async def llms_txt():
    return LLMS_TXT


@router.get("/llms-full.txt", response_class=PlainTextResponse, include_in_schema=False)
async def llms_full_txt():
    return LLMS_TXT


@router.get("/api/meta/models", summary="Distinct model names")
async def distinct_models() -> list[str]:
    return await get_distinct_models()


@router.get("/api/meta/tags", summary="Distinct tags")
async def distinct_tags() -> list[str]:
    return await get_distinct_tags()
