"""Simple executor: chat loop against an OpenAI-compatible endpoint with tool use."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from .tools import TOOL_DEFINITIONS, Sandbox, ToolResult

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a coding assistant. Solve the given task by writing code.
Use the provided tools to write files, read files, and run commands in your workspace.
When you are done, respond with your final answer as plain text.\
"""

MAX_TURNS = 30
REQUEST_TIMEOUT = 120.0


@dataclass
class ExecutorEvent:
    """A captured event from the executor run."""

    kind: str  # model | tool
    timestamp: int  # epoch ms
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutorResult:
    """The complete result of running one task through the executor."""

    messages: list[dict[str, Any]]
    events: list[ExecutorEvent]
    output: str | None = None
    error: str | None = None
    started_at: int = 0
    completed_at: int = 0


def _epoch_ms() -> int:
    return int(time.time() * 1000)


async def run_task(
    *,
    task_input: str,
    model: str,
    model_url: str,
    sandbox: Sandbox,
    max_turns: int = MAX_TURNS,
) -> ExecutorResult:
    """Run a single task through the chat loop.

    Sends the task to the model, handles tool calls, and captures all events.
    """
    started_at = _epoch_ms()
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task_input},
    ]
    events: list[ExecutorEvent] = []
    final_output: str | None = None
    error: str | None = None

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        for turn in range(max_turns):
            try:
                response = await client.post(
                    f"{model_url}/chat/completions",
                    json={
                        "model": model,
                        "messages": messages,
                        "tools": TOOL_DEFINITIONS,
                    },
                )
                response.raise_for_status()
                body = response.json()
            except httpx.HTTPError as e:
                error = f"HTTP error on turn {turn}: {e}"
                logger.error(error)
                break

            choice = body["choices"][0]
            assistant_msg = choice["message"]
            usage = body.get("usage", {})

            # Record model event
            events.append(
                ExecutorEvent(
                    kind="model",
                    timestamp=_epoch_ms(),
                    data={
                        "role": "assistant",
                        "content": assistant_msg.get("content"),
                        "tool_calls": assistant_msg.get("tool_calls"),
                        "usage": {
                            "input_tokens": usage.get("prompt_tokens", 0),
                            "output_tokens": usage.get("completion_tokens", 0),
                            "total_tokens": usage.get("total_tokens", 0),
                        },
                    },
                )
            )

            # Append assistant message to conversation
            messages.append(assistant_msg)

            # Check for tool calls
            tool_calls = assistant_msg.get("tool_calls")
            if not tool_calls:
                # Model is done — its text is the final output
                final_output = assistant_msg.get("content", "")
                break

            # Execute each tool call
            for tc in tool_calls:
                fn_name = tc["function"]["name"]
                try:
                    fn_args = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    fn_args = {}

                result: ToolResult = await sandbox.execute(fn_name, fn_args)

                # Record tool event
                events.append(
                    ExecutorEvent(
                        kind="tool",
                        timestamp=_epoch_ms(),
                        data={
                            "id": tc["id"],
                            "function": fn_name,
                            "arguments": fn_args,
                            "result": result.output if not result.error else None,
                            "error": result.error,
                            "duration_ms": result.duration_ms,
                        },
                    )
                )

                # Append tool result to conversation
                tool_content = result.output if not result.error else f"Error: {result.error}"
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": tool_content,
                    }
                )
        else:
            error = f"Reached max turns ({max_turns})"
            logger.warning(error)

    return ExecutorResult(
        messages=messages,
        events=events,
        output=final_output,
        error=error,
        started_at=started_at,
        completed_at=_epoch_ms(),
    )
