"""Pydantic v2 models for the trajectory viewer.

These mirror the subset of Inspect AI's EvalLog/EvalSample types that we use.
Field names match Inspect's where they exist.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------


class TokenUsage(BaseModel):
    """Token counts for a model event."""

    input_tokens: int = Field(description="Prompt / input tokens")
    output_tokens: int = Field(description="Completion / output tokens")
    total_tokens: int = Field(description="Sum of input + output tokens")


class Score(BaseModel):
    """A single scorer's result. Matches Inspect's Score shape."""

    value: str | float | dict[str, float] = Field(
        description='Categorical ("C"/"I"/"P"), numeric, or dict of named dimensions'
    )
    answer: str | None = Field(default=None, description="Model's answer text")
    explanation: str | None = Field(
        default=None, description="Scorer's rationale"
    )
    metadata: dict[str, Any] | None = Field(
        default=None, description="Extra scorer-specific data"
    )


class Message(BaseModel):
    """Chat message in the messages projection."""

    role: str = Field(description="user | assistant | tool | system")
    content: str = Field(description="Message text")
    tool_call_id: str | None = Field(
        default=None, description="Tool call ID for tool messages"
    )


class Event(BaseModel):
    """One event in the trajectory transcript.

    The `event` field determines the kind; remaining fields vary by kind.
    We store the full payload as-is from Inspect.
    """

    event: str = Field(
        description="Event kind: model | tool | compaction | score | error | info | input | sample_init | sample_limit | span_begin | span_end | ..."
    )
    timestamp: int | None = Field(
        default=None, description="Epoch milliseconds"
    )

    # model events
    role: str | None = None
    output: str | None = None
    usage: TokenUsage | None = None

    # tool events
    id: str | None = None
    function: str | None = None
    arguments: Any | None = None
    result: Any | None = None
    error: str | None = None
    duration_ms: int | None = None

    # compaction events
    before_tokens: int | None = None
    after_tokens: int | None = None
    summary: str | None = None

    # score events
    name: str | None = None
    score: Score | None = None

    # span events
    span_id: str | None = None
    span_name: str | None = None

    # catch-all for event types we don't explicitly model
    extra: dict[str, Any] | None = Field(
        default=None, description="Additional fields for unmodeled event types"
    )


# ---------------------------------------------------------------------------
# Trajectory
# ---------------------------------------------------------------------------


class TrajectoryCreate(BaseModel):
    """Payload for POST /api/trajectories — compact trajectory JSON."""

    id: str = Field(description="Globally unique trajectory ID")
    run_id: str | None = Field(
        default=None, description="Groups trajectories from the same EvalLog"
    )
    task: str | None = Field(default=None, description="Task name (e.g. humaneval)")
    task_id: str | None = Field(
        default=None, description="Specific task ID (e.g. humaneval/42)"
    )
    model: str = Field(description="Model name")
    harness: str | None = Field(
        default=None, description="Harness identifier (e.g. opencode@0.1.4)"
    )
    status: str = Field(description="started | success | error")
    started_at: int = Field(description="Epoch ms")
    completed_at: int | None = Field(default=None, description="Epoch ms")

    input: str = Field(description="Starting prompt")
    target: str | None = Field(default=None, description="Expected answer")
    output: str | None = Field(default=None, description="Model's final output")
    error: str | None = Field(default=None, description="Error message if status=error")

    messages: list[Message] | None = Field(
        default=None, description="Chat message projection"
    )
    events: list[Event] = Field(
        default_factory=list, description="Full event transcript"
    )
    scores: dict[str, Score] | None = Field(
        default=None, description="Scorer results keyed by scorer name"
    )
    metadata: dict[str, Any] | None = Field(
        default=None, description="Arbitrary metadata"
    )


class TrajectorySummary(BaseModel):
    """Lightweight trajectory info for list views and SSE."""

    id: str
    run_id: str | None = None
    task: str | None = None
    task_id: str | None = None
    model: str
    harness: str | None = None
    status: str
    started_at: int
    completed_at: int | None = None
    duration_ms: int | None = None

    step_count: int = 0
    tool_call_count: int = 0
    compaction_count: int = 0
    total_tokens: int | None = None
    tool_names: str | None = None
    eval_verdict: str | None = None
    eval_score: float | None = None
    tags: list[str] = Field(default_factory=list)


class Trajectory(TrajectorySummary):
    """Full trajectory with events, scores, messages."""

    input: str
    target: str | None = None
    output: str | None = None
    error: str | None = None

    messages: list[Message] = Field(default_factory=list)
    events: list[Event] = Field(default_factory=list)
    scores: dict[str, Score] = Field(default_factory=dict)
    metadata: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Runs
# ---------------------------------------------------------------------------


class RunSummary(BaseModel):
    """Run list entry."""

    id: str
    task: str | None = None
    model: str | None = None
    created_at: int | None = None
    status: str | None = None
    sample_count: int = 0


class Run(RunSummary):
    """Full run detail."""

    stats: dict[str, Any] | None = None
    eval_spec: dict[str, Any] | None = None
    trajectories: list[TrajectorySummary] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


class SearchRequest(BaseModel):
    """POST /api/search body."""

    sql: str = Field(description="SQL query against v_trajectories")


class SearchColumn(BaseModel):
    """Column metadata for autocomplete."""

    name: str
    type: str
    description: str


class SearchResponse(BaseModel):
    """Search result."""

    columns: list[str]
    rows: list[dict[str, Any]]
    took_ms: float
    truncated: bool = False


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------


class TagCreate(BaseModel):
    """POST /api/trajectories/{id}/tags body."""

    tag: str = Field(description="Tag string")


# ---------------------------------------------------------------------------
# SSE
# ---------------------------------------------------------------------------


class SSEEvent(BaseModel):
    """Shape of an SSE event."""

    event: str = Field(description="Event type: trajectory.created, trajectory.updated, run.created, trajectory.tagged, trajectory.untagged")
    data: dict[str, Any]


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ErrorDetail(BaseModel):
    """Structured error."""

    code: str
    message: str
    details: dict[str, Any] | None = None


class ErrorEnvelope(BaseModel):
    """Standard error response."""

    error: ErrorDetail
