"""Sandbox tools that the model can call during task execution."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# OpenAI function-calling tool definitions sent to the model.
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file in the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path within the workspace.",
                    },
                    "content": {
                        "type": "string",
                        "description": "File content to write.",
                    },
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the content of a file in the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path within the workspace.",
                    },
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Run a shell command in the workspace directory. Use for running tests, installing packages, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to execute.",
                    },
                },
                "required": ["command"],
            },
        },
    },
]


@dataclass
class ToolResult:
    """Result of executing a tool call."""

    output: str
    error: str | None = None
    duration_ms: int = 0


class Sandbox:
    """A sandboxed workspace directory for tool execution."""

    def __init__(self, workdir: Path) -> None:
        self.workdir = workdir
        self.workdir.mkdir(parents=True, exist_ok=True)

    def _resolve(self, path: str) -> Path:
        """Resolve a relative path within the sandbox, preventing escapes."""
        resolved = (self.workdir / path).resolve()
        if not str(resolved).startswith(str(self.workdir.resolve())):
            raise ValueError(f"Path escapes sandbox: {path}")
        return resolved

    async def execute(self, function: str, arguments: dict[str, Any]) -> ToolResult:
        """Execute a tool call and return the result."""
        import time

        start = time.monotonic()
        try:
            if function == "write_file":
                result = await self._write_file(arguments["path"], arguments["content"])
            elif function == "read_file":
                result = await self._read_file(arguments["path"])
            elif function == "run_command":
                result = await self._run_command(arguments["command"])
            else:
                result = ToolResult(output="", error=f"Unknown tool: {function}")
        except Exception as e:
            result = ToolResult(output="", error=str(e))
        result.duration_ms = int((time.monotonic() - start) * 1000)
        return result

    async def _write_file(self, path: str, content: str) -> ToolResult:
        resolved = self._resolve(path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content)
        return ToolResult(output=f"Wrote {len(content)} bytes to {path}")

    async def _read_file(self, path: str) -> ToolResult:
        resolved = self._resolve(path)
        if not resolved.exists():
            return ToolResult(output="", error=f"File not found: {path}")
        content = resolved.read_text()
        return ToolResult(output=content)

    async def _run_command(self, command: str) -> ToolResult:
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.workdir,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
            output = stdout.decode(errors="replace")
            err_output = stderr.decode(errors="replace")
            if proc.returncode != 0:
                return ToolResult(
                    output=output,
                    error=f"Exit code {proc.returncode}\n{err_output}".strip(),
                )
            return ToolResult(output=(output + err_output).strip())
        except asyncio.TimeoutError:
            return ToolResult(output="", error="Command timed out after 30s")
