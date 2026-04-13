"""SQLite database layer using aiosqlite.

Single-file DB, WAL mode, read-only connection for search.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import aiosqlite

from trajectory_schema import (
    Event,
    Score,
    Trajectory,
    TrajectoryCreate,
    TrajectorySummary,
)

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schema.sql"

_db: aiosqlite.Connection | None = None
_db_ro: aiosqlite.Connection | None = None


async def init(db_path: str = "data/viewer.db") -> None:
    """Open DB connections and apply schema."""
    global _db, _db_ro
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    _db = await aiosqlite.connect(db_path)
    _db.row_factory = aiosqlite.Row
    await _db.execute("PRAGMA journal_mode = WAL")
    await _db.execute("PRAGMA foreign_keys = ON")

    schema = SCHEMA_PATH.read_text()
    await _db.executescript(schema)

    # Read-only connection for user SQL search
    _db_ro = await aiosqlite.connect(f"file:{db_path}?mode=ro", uri=True)
    _db_ro.row_factory = aiosqlite.Row
    await _db_ro.execute("PRAGMA query_only = ON")


async def close() -> None:
    global _db, _db_ro
    if _db:
        await _db.close()
        _db = None
    if _db_ro:
        await _db_ro.close()
        _db_ro = None


def get_db() -> aiosqlite.Connection:
    assert _db is not None, "Database not initialized"
    return _db


def get_db_ro() -> aiosqlite.Connection:
    assert _db_ro is not None, "Database not initialized"
    return _db_ro


# ---------------------------------------------------------------------------
# Score normalization
# ---------------------------------------------------------------------------


def normalize_score(value: str | float | dict[str, float]) -> tuple[float | None, str | None]:
    """Convert a Score.value to (score_numeric, verdict)."""
    if isinstance(value, str):
        mapping = {"C": ("pass", 1.0), "I": ("fail", 0.0), "P": ("partial", 0.5)}
        if value in mapping:
            verdict, numeric = mapping[value]
            return numeric, verdict
        return None, None
    if isinstance(value, (int, float)):
        return float(value), None
    if isinstance(value, dict):
        vals = [v for v in value.values() if isinstance(v, (int, float))]
        return (sum(vals) / len(vals) if vals else None), None
    return None, None


# ---------------------------------------------------------------------------
# Derived fields
# ---------------------------------------------------------------------------


def compute_derived(traj: TrajectoryCreate) -> dict[str, Any]:
    """Compute derived fields from events and scores."""
    step_count = len(traj.events)
    tool_events = [e for e in traj.events if e.event == "tool"]
    tool_call_count = len(tool_events)
    compaction_count = sum(1 for e in traj.events if e.event == "compaction")
    total_tokens = sum(
        e.usage.total_tokens
        for e in traj.events
        if e.event == "model" and e.usage
    )
    duration_ms = (
        (traj.completed_at - traj.started_at)
        if traj.completed_at and traj.started_at
        else None
    )
    tool_names = ",".join(sorted({e.function for e in tool_events if e.function}))

    eval_verdict = None
    eval_score = None
    if traj.scores:
        first_score = next(iter(traj.scores.values()))
        eval_score, eval_verdict = normalize_score(first_score.value)

    return {
        "step_count": step_count,
        "tool_call_count": tool_call_count,
        "compaction_count": compaction_count,
        "total_tokens": total_tokens or None,
        "duration_ms": duration_ms,
        "tool_names": tool_names or None,
        "eval_verdict": eval_verdict,
        "eval_score": eval_score,
    }


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


async def insert_trajectory(traj: TrajectoryCreate) -> TrajectorySummary:
    """Insert a full trajectory and return the summary."""
    db = get_db()
    derived = compute_derived(traj)

    # Ensure run exists if run_id provided
    if traj.run_id:
        await db.execute(
            "INSERT OR IGNORE INTO runs (id, task, model, created_at, status) VALUES (?, ?, ?, ?, ?)",
            (traj.run_id, traj.task, traj.model, traj.started_at, traj.status),
        )

    await db.execute(
        """INSERT OR REPLACE INTO trajectories
        (id, run_id, task, task_id, model, harness, status, started_at, completed_at,
         input, target, output, error,
         step_count, tool_call_count, compaction_count, total_tokens, duration_ms,
         tool_names, eval_verdict, eval_score, metadata, raw_sample)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            traj.id, traj.run_id, traj.task, traj.task_id, traj.model, traj.harness,
            traj.status, traj.started_at, traj.completed_at,
            traj.input, traj.target, traj.output, traj.error,
            derived["step_count"], derived["tool_call_count"], derived["compaction_count"],
            derived["total_tokens"], derived["duration_ms"], derived["tool_names"],
            derived["eval_verdict"], derived["eval_score"],
            json.dumps(traj.metadata) if traj.metadata else None,
            traj.model_dump_json(),
        ),
    )

    # Insert events
    for idx, event in enumerate(traj.events):
        await db.execute(
            "INSERT OR REPLACE INTO events (trajectory_id, idx, kind, timestamp, payload) VALUES (?, ?, ?, ?, ?)",
            (traj.id, idx, event.event, event.timestamp, event.model_dump_json()),
        )

    # Insert scores
    if traj.scores:
        for name, score in traj.scores.items():
            score_numeric, verdict = normalize_score(score.value)
            await db.execute(
                """INSERT INTO scores (trajectory_id, name, value_raw, score_numeric, verdict, answer, explanation, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    traj.id, name, json.dumps(score.value), score_numeric, verdict,
                    score.answer, score.explanation,
                    json.dumps(score.metadata) if score.metadata else None,
                ),
            )

    await db.commit()

    return TrajectorySummary(
        id=traj.id,
        run_id=traj.run_id,
        task=traj.task,
        task_id=traj.task_id,
        model=traj.model,
        harness=traj.harness,
        status=traj.status,
        started_at=traj.started_at,
        completed_at=traj.completed_at,
        duration_ms=derived["duration_ms"],
        step_count=derived["step_count"],
        tool_call_count=derived["tool_call_count"],
        compaction_count=derived["compaction_count"],
        total_tokens=derived["total_tokens"],
        tool_names=derived["tool_names"],
        eval_verdict=derived["eval_verdict"],
        eval_score=derived["eval_score"],
        tags=[],
    )


async def get_trajectory(traj_id: str) -> Trajectory | None:
    """Fetch full trajectory by ID."""
    db = get_db()
    row = await db.execute_fetchall(
        "SELECT * FROM trajectories WHERE id = ?", (traj_id,)
    )
    if not row:
        return None
    r = dict(row[0])

    # Fetch events
    event_rows = await db.execute_fetchall(
        "SELECT payload FROM events WHERE trajectory_id = ? ORDER BY idx", (traj_id,)
    )
    events = [Event.model_validate_json(er["payload"]) for er in event_rows]

    # Fetch scores
    score_rows = await db.execute_fetchall(
        "SELECT name, value_raw, answer, explanation, metadata FROM scores WHERE trajectory_id = ?",
        (traj_id,),
    )
    scores = {}
    for sr in score_rows:
        scores[sr["name"]] = Score(
            value=json.loads(sr["value_raw"]),
            answer=sr["answer"],
            explanation=sr["explanation"],
            metadata=json.loads(sr["metadata"]) if sr["metadata"] else None,
        )

    # Fetch tags
    tag_rows = await db.execute_fetchall(
        "SELECT tag FROM tags WHERE trajectory_id = ?", (traj_id,)
    )
    tag_list = [tr["tag"] for tr in tag_rows]

    # Derive messages from events if not stored
    messages = []
    if r.get("raw_sample"):
        raw = json.loads(r["raw_sample"])
        if raw.get("messages"):
            messages = raw["messages"]

    return Trajectory(
        id=r["id"],
        run_id=r["run_id"],
        task=r["task"],
        task_id=r["task_id"],
        model=r["model"],
        harness=r["harness"],
        status=r["status"],
        started_at=r["started_at"],
        completed_at=r["completed_at"],
        duration_ms=r["duration_ms"],
        step_count=r["step_count"],
        tool_call_count=r["tool_call_count"],
        compaction_count=r["compaction_count"],
        total_tokens=r["total_tokens"],
        tool_names=r["tool_names"],
        eval_verdict=r["eval_verdict"],
        eval_score=r["eval_score"],
        tags=tag_list,
        input=r["input"],
        target=r["target"],
        output=r["output"],
        error=r["error"],
        messages=messages,
        events=events,
        scores=scores,
        metadata=json.loads(r["metadata"]) if r["metadata"] else None,
    )


async def list_trajectories(
    limit: int = 50,
    cursor: int | None = None,
    run_id: str | None = None,
) -> list[TrajectorySummary]:
    """List trajectories, newest first."""
    db = get_db()
    conditions = []
    params: list[Any] = []

    if cursor is not None:
        conditions.append("t.started_at < ?")
        params.append(cursor)
    if run_id:
        conditions.append("t.run_id = ?")
        params.append(run_id)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    query = f"""
        SELECT t.*,
            (SELECT GROUP_CONCAT(tag, ',') FROM tags WHERE trajectory_id = t.id) AS tags_csv
        FROM trajectories t
        {where}
        ORDER BY t.started_at DESC
        LIMIT ?
    """
    params.append(limit)

    rows = await db.execute_fetchall(query, params)
    results = []
    for r in rows:
        r = dict(r)
        tags = r.get("tags_csv", "") or ""
        results.append(
            TrajectorySummary(
                id=r["id"],
                run_id=r["run_id"],
                task=r["task"],
                task_id=r["task_id"],
                model=r["model"],
                harness=r["harness"],
                status=r["status"],
                started_at=r["started_at"],
                completed_at=r["completed_at"],
                duration_ms=r["duration_ms"],
                step_count=r["step_count"],
                tool_call_count=r["tool_call_count"],
                compaction_count=r["compaction_count"],
                total_tokens=r["total_tokens"],
                tool_names=r["tool_names"],
                eval_verdict=r["eval_verdict"],
                eval_score=r["eval_score"],
                tags=[t for t in tags.split(",") if t],
            )
        )
    return results


async def list_runs(limit: int = 50) -> list[dict[str, Any]]:
    """List runs with sample counts."""
    db = get_db()
    rows = await db.execute_fetchall(
        """SELECT r.*, COUNT(t.id) AS sample_count
           FROM runs r LEFT JOIN trajectories t ON t.run_id = r.id
           GROUP BY r.id
           ORDER BY r.created_at DESC
           LIMIT ?""",
        (limit,),
    )
    return [dict(r) for r in rows]


async def get_run(run_id: str) -> dict[str, Any] | None:
    """Fetch a single run."""
    db = get_db()
    rows = await db.execute_fetchall(
        """SELECT r.*, COUNT(t.id) AS sample_count
           FROM runs r LEFT JOIN trajectories t ON t.run_id = r.id
           WHERE r.id = ?
           GROUP BY r.id""",
        (run_id,),
    )
    return dict(rows[0]) if rows else None


async def add_tag(traj_id: str, tag: str) -> bool:
    """Add a tag. Returns True if added, False if already exists."""
    db = get_db()
    try:
        await db.execute(
            "INSERT INTO tags (trajectory_id, tag, created_at) VALUES (?, ?, ?)",
            (traj_id, tag, int(time.time() * 1000)),
        )
        await db.commit()
        return True
    except Exception:
        return False


async def remove_tag(traj_id: str, tag: str) -> bool:
    """Remove a tag. Returns True if removed."""
    db = get_db()
    cursor = await db.execute(
        "DELETE FROM tags WHERE trajectory_id = ? AND tag = ?",
        (traj_id, tag),
    )
    await db.commit()
    return cursor.rowcount > 0


async def search(sql: str) -> tuple[list[str], list[dict[str, Any]], bool]:
    """Execute a validated SQL query. Returns (columns, rows, truncated)."""
    db_ro = get_db_ro()
    cursor = await db_ro.execute(sql)
    columns = [desc[0] for desc in cursor.description] if cursor.description else []
    rows_raw = await cursor.fetchall()
    rows = [dict(zip(columns, row)) for row in rows_raw]
    truncated = len(rows) >= 500
    return columns, rows, truncated


async def get_distinct_models() -> list[str]:
    """Get distinct model names."""
    db = get_db()
    rows = await db.execute_fetchall(
        "SELECT DISTINCT model FROM trajectories ORDER BY model"
    )
    return [r["model"] for r in rows]


async def get_distinct_tags() -> list[str]:
    """Get distinct tags."""
    db = get_db()
    rows = await db.execute_fetchall(
        "SELECT DISTINCT tag FROM tags ORDER BY tag"
    )
    return [r["tag"] for r in rows]
