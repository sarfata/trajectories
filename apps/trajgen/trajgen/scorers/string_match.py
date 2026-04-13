"""String match scorer: exact or regex match on model output."""

from __future__ import annotations

import re

from trajectory_schema import Score as CompactScore

from ..tasks import ScorerConfig


async def score(
    output: str | None,
    target: str | None,
    cfg: ScorerConfig,
) -> dict[str, CompactScore]:
    """Score by matching output against expected pattern or target."""
    expected = cfg.expected or target or ""
    actual = (output or "").strip()

    if cfg.regex:
        match = bool(re.search(expected, actual))
    else:
        match = actual == expected.strip()

    return {
        "string_match": CompactScore(
            value="C" if match else "I",
            answer=actual,
            explanation=f"{'Match' if match else 'No match'} against {'regex' if cfg.regex else 'exact'}: {expected!r}",
        )
    }
