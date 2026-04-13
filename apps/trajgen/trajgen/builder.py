"""Build Inspect AI EvalLog/EvalSample objects and compact trajectory JSON from executor results."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from inspect_ai.log import (
    EvalConfig,
    EvalDataset,
    EvalLog,
    EvalPlan,
    EvalResults,
    EvalSample,
    EvalSpec,
    EvalStats,
)
from inspect_ai.model import (
    ChatMessageAssistant,
    ChatMessageSystem,
    ChatMessageTool,
    ChatMessageUser,
    ModelOutput,
    ModelUsage,
)
from inspect_ai.scorer import Score

from trajectory_schema import TrajectoryCreate
from trajectory_schema import Event as CompactEvent
from trajectory_schema import Score as CompactScore
from trajectory_schema import TokenUsage, Message

from .executor import ExecutorEvent, ExecutorResult
from .tasks import Task


def _make_id(prefix: str) -> str:
    short = uuid.uuid4().hex[:12]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{ts}_{short}"


def _to_inspect_messages(messages: list[dict[str, Any]]) -> list:
    """Convert raw message dicts to Inspect ChatMessage objects."""
    result = []
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content") or ""
        if role == "system":
            result.append(ChatMessageSystem(content=content))
        elif role == "user":
            result.append(ChatMessageUser(content=content))
        elif role == "assistant":
            result.append(ChatMessageAssistant(content=content))
        elif role == "tool":
            result.append(
                ChatMessageTool(
                    content=content,
                    tool_call_id=msg.get("tool_call_id", ""),
                )
            )
    return result


def build_eval_sample(
    task: Task,
    result: ExecutorResult,
    scores: dict[str, Score] | None = None,
) -> EvalSample:
    """Build an Inspect EvalSample from an executor result."""
    return EvalSample(
        id=task.id,
        epoch=1,
        input=task.input,
        target=task.target or "",
        messages=_to_inspect_messages(result.messages),
        output=ModelOutput(
            model="",
            choices=[],
            completion=result.output or "",
        ),
        scores=scores or {},
        metadata=task.metadata,
    )


def build_eval_log(
    sample: EvalSample,
    *,
    model: str,
    task_name: str,
    run_id: str | None = None,
    started_at: int = 0,
    completed_at: int = 0,
    error_msg: str | None = None,
) -> EvalLog:
    """Build an Inspect EvalLog wrapping a single sample."""
    rid = run_id or _make_id("run")
    status = "error" if error_msg else "success"

    start_dt = datetime.fromtimestamp(started_at / 1000, tz=timezone.utc) if started_at else datetime.now(timezone.utc)
    end_dt = datetime.fromtimestamp(completed_at / 1000, tz=timezone.utc) if completed_at else datetime.now(timezone.utc)

    spec = EvalSpec(
        task=task_name,
        task_id=sample.id if isinstance(sample.id, str) else str(sample.id),
        model=model,
        created=start_dt.isoformat(),
        run_id=rid,
        config=EvalConfig(),
        dataset=EvalDataset(name=task_name, samples=1),
    )

    stats = EvalStats(
        started_at=start_dt.isoformat(),
        completed_at=end_dt.isoformat(),
    )

    return EvalLog(
        status=status,
        eval=spec,
        plan=EvalPlan(),
        results=EvalResults(total_samples=1, completed_samples=1),
        stats=stats,
        samples=[sample],
    )


def build_compact_trajectory(
    task: Task,
    result: ExecutorResult,
    *,
    model: str,
    run_id: str | None = None,
    scores: dict[str, CompactScore] | None = None,
) -> TrajectoryCreate:
    """Build the compact trajectory JSON for POSTing to the viewer."""
    traj_id = _make_id("traj")
    status = "error" if result.error else "success"

    # Build compact events
    compact_events: list[CompactEvent] = []
    for ev in result.events:
        if ev.kind == "model":
            usage_data = ev.data.get("usage", {})
            compact_events.append(
                CompactEvent(
                    event="model",
                    timestamp=ev.timestamp,
                    role="assistant",
                    output=ev.data.get("content"),
                    usage=TokenUsage(
                        input_tokens=usage_data.get("input_tokens", 0),
                        output_tokens=usage_data.get("output_tokens", 0),
                        total_tokens=usage_data.get("total_tokens", 0),
                    ),
                )
            )
        elif ev.kind == "tool":
            compact_events.append(
                CompactEvent(
                    event="tool",
                    timestamp=ev.timestamp,
                    id=ev.data.get("id"),
                    function=ev.data.get("function"),
                    arguments=ev.data.get("arguments"),
                    result=ev.data.get("result"),
                    error=ev.data.get("error"),
                    duration_ms=ev.data.get("duration_ms"),
                )
            )

    # Build compact messages
    compact_messages: list[Message] = []
    for msg in result.messages:
        role = msg.get("role", "")
        if role == "system":
            continue
        compact_messages.append(
            Message(
                role=role,
                content=msg.get("content") or "",
                tool_call_id=msg.get("tool_call_id"),
            )
        )

    return TrajectoryCreate(
        id=traj_id,
        run_id=run_id,
        task=task.id.split("/")[0] if "/" in task.id else task.id,
        task_id=task.id,
        model=model,
        harness="trajgen@0.1.0",
        status=status,
        started_at=result.started_at,
        completed_at=result.completed_at,
        input=task.input,
        target=task.target,
        output=result.output,
        error=result.error,
        messages=compact_messages,
        events=compact_events,
        scores=scores,
        metadata=task.metadata or None,
    )
