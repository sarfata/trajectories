"""SQL search safety layer using sqlglot."""

from __future__ import annotations

import sqlglot
from sqlglot import exp

from trajectory_schema import ErrorDetail

ALLOWED_TABLES = {"v_trajectories"}


def validate_sql(sql: str) -> ErrorDetail | str:
    """Parse and validate user SQL. Returns validated SQL string or ErrorDetail."""
    try:
        statements = sqlglot.parse(sql, dialect="sqlite")
    except sqlglot.errors.ParseError as e:
        return ErrorDetail(
            code="sql_parse_error",
            message=str(e),
            details={"raw": sql},
        )

    if len(statements) != 1:
        return ErrorDetail(
            code="sql_parse_error",
            message="Exactly one SELECT statement is required.",
            details={"statement_count": len(statements)},
        )

    stmt = statements[0]
    if stmt is None or not isinstance(stmt, exp.Select):
        return ErrorDetail(
            code="sql_parse_error",
            message="Only SELECT statements are allowed.",
        )

    # Check table references
    for table in stmt.find_all(exp.Table):
        table_name = table.name
        if table_name and table_name not in ALLOWED_TABLES:
            return ErrorDetail(
                code="sql_forbidden_table",
                message=f"Table '{table_name}' is not allowed. Use v_trajectories.",
                details={"table": table_name},
            )

    # Reject subqueries that reference other tables (defense in depth)
    for sub in stmt.find_all(exp.Subquery):
        for table in sub.find_all(exp.Table):
            if table.name and table.name not in ALLOWED_TABLES:
                return ErrorDetail(
                    code="sql_forbidden_table",
                    message=f"Table '{table.name}' in subquery is not allowed.",
                    details={"table": table.name},
                )

    # Wrap with LIMIT 500
    wrapped = f"SELECT * FROM ({sql}) AS q LIMIT 500"
    return wrapped


SEARCH_COLUMNS = [
    {"name": "id", "type": "TEXT", "description": "Trajectory ID"},
    {"name": "run_id", "type": "TEXT", "description": "Run ID (groups trajectories from the same eval)"},
    {"name": "task", "type": "TEXT", "description": "Task name (e.g. humaneval)"},
    {"name": "task_id", "type": "TEXT", "description": "Specific task ID (e.g. humaneval/42)"},
    {"name": "model", "type": "TEXT", "description": "Model name"},
    {"name": "harness", "type": "TEXT", "description": "Harness identifier"},
    {"name": "status", "type": "TEXT", "description": "started | success | error"},
    {"name": "started_at", "type": "INTEGER", "description": "Start time (epoch ms)"},
    {"name": "completed_at", "type": "INTEGER", "description": "End time (epoch ms)"},
    {"name": "duration_ms", "type": "INTEGER", "description": "Duration in milliseconds"},
    {"name": "step_count", "type": "INTEGER", "description": "Total number of events"},
    {"name": "tool_call_count", "type": "INTEGER", "description": "Number of tool call events"},
    {"name": "compaction_count", "type": "INTEGER", "description": "Number of compaction events"},
    {"name": "total_tokens", "type": "INTEGER", "description": "Sum of all model event tokens"},
    {"name": "tool_names", "type": "TEXT", "description": "Comma-separated distinct tool names used"},
    {"name": "eval_verdict", "type": "TEXT", "description": "Normalized verdict: pass | fail | partial"},
    {"name": "eval_score", "type": "REAL", "description": "Normalized numeric score"},
    {"name": "tags", "type": "TEXT", "description": "Comma-separated user tags"},
    {"name": "scorers", "type": "TEXT", "description": "Comma-separated scorer names"},
]

EXAMPLE_QUERIES = [
    {
        "title": "Failing runs with the most tool calls",
        "sql": "SELECT id, model, tool_call_count, total_tokens, eval_verdict\nFROM v_trajectories\nWHERE eval_verdict = 'fail'\nORDER BY tool_call_count DESC",
    },
    {
        "title": "Runs that required compaction",
        "sql": "SELECT id, model, compaction_count, total_tokens\nFROM v_trajectories\nWHERE compaction_count > 0",
    },
    {
        "title": "Runs tagged 'interesting'",
        "sql": "SELECT id, task_id, eval_score\nFROM v_trajectories\nWHERE tags LIKE '%interesting%'",
    },
    {
        "title": "Which tools appear most often in failing runs",
        "sql": "SELECT tool_names, COUNT(*) AS n\nFROM v_trajectories\nWHERE eval_verdict = 'fail'\nGROUP BY tool_names\nORDER BY n DESC",
    },
    {
        "title": "Compare models on the same tasks",
        "sql": "SELECT task_id, model, eval_score, total_tokens, duration_ms\nFROM v_trajectories\nWHERE task_id IN (SELECT task_id FROM v_trajectories GROUP BY task_id HAVING COUNT(DISTINCT model) > 1)\nORDER BY task_id, model",
    },
]
