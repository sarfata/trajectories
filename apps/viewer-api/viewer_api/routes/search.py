"""SQL search routes."""

from __future__ import annotations

import asyncio
import time

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from trajectory_schema import ErrorDetail, SearchRequest, SearchResponse

from ..db import search as db_search
from ..search import EXAMPLE_QUERIES, SEARCH_COLUMNS, validate_sql

router = APIRouter(prefix="/api", tags=["search"])


def _error_response(detail: ErrorDetail, status: int = 400) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": detail.model_dump()},
    )


@router.post(
    "/search",
    response_model=SearchResponse,
    summary="Run a SQL query",
    description="Execute a read-only SQL SELECT against v_trajectories. 5s timeout, 500 row limit.",
)
async def search_route(body: SearchRequest) -> SearchResponse | JSONResponse:
    result = validate_sql(body.sql)
    if isinstance(result, ErrorDetail):
        return _error_response(result)

    start = time.monotonic()
    try:
        columns, rows, truncated = await asyncio.wait_for(
            db_search(result), timeout=5.0
        )
    except asyncio.TimeoutError:
        return _error_response(
            ErrorDetail(
                code="sql_timeout",
                message="Query exceeded 5 second timeout.",
            ),
            status=408,
        )
    except Exception as e:
        return _error_response(
            ErrorDetail(
                code="sql_execution_error",
                message=str(e),
            )
        )
    took_ms = (time.monotonic() - start) * 1000

    return SearchResponse(
        columns=columns, rows=rows, took_ms=round(took_ms, 2), truncated=truncated
    )


@router.get(
    "/search/columns",
    summary="List searchable columns",
    description="Column metadata for SQL autocomplete.",
)
async def search_columns() -> list[dict]:
    return SEARCH_COLUMNS


@router.get(
    "/search/examples",
    summary="Example SQL queries",
    description="Curated example queries for the search box.",
)
async def search_examples() -> list[dict]:
    return EXAMPLE_QUERIES
