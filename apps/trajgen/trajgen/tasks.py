"""Load tasks from JSONL files."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ScorerConfig:
    kind: str
    # string_match
    expected: str | None = None
    regex: bool = False
    # pytest
    test_file: str | None = None
    tests: str | None = None  # inline test code, written to sandbox as test_file
    # llm_judge
    model: str | None = None
    rubric: list[str] = field(default_factory=list)


@dataclass
class Task:
    id: str
    input: str
    target: str | None = None
    scorer: ScorerConfig | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def load_tasks(path: Path) -> list[Task]:
    """Load tasks from a JSONL file. Each line is one JSON object."""
    tasks: list[Task] = []
    with open(path) as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            scorer = None
            if "scorer" in raw:
                s = raw["scorer"]
                scorer = ScorerConfig(
                    kind=s["kind"],
                    expected=s.get("expected"),
                    regex=s.get("regex", False),
                    test_file=s.get("test_file"),
                    tests=s.get("tests"),
                    model=s.get("model"),
                    rubric=s.get("rubric", []),
                )
            tasks.append(
                Task(
                    id=raw["id"],
                    input=raw["input"],
                    target=raw.get("target"),
                    scorer=scorer,
                    metadata=raw.get("metadata", {}),
                )
            )
    return tasks
