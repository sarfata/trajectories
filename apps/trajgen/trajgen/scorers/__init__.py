"""Pluggable scorers. Each module exposes: async def score(...) -> dict[str, CompactScore]"""

from __future__ import annotations

from pathlib import Path

from trajectory_schema import Score as CompactScore

from ..tasks import ScorerConfig


async def run_scorer(
    output: str | None,
    target: str | None,
    cfg: ScorerConfig | None,
    sandbox_dir: Path | None = None,
) -> dict[str, CompactScore]:
    """Dispatch to the appropriate scorer based on config."""
    if cfg is None:
        return {}

    if cfg.kind == "string_match":
        from .string_match import score
        return await score(output, target, cfg)
    elif cfg.kind == "pytest":
        from .pytest_scorer import score
        return await score(output, target, cfg, sandbox_dir=sandbox_dir)
    else:
        return {}
