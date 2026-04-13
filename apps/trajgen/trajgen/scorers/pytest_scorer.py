"""Pytest scorer: runs tests against files the model wrote in the sandbox.

Two modes:
  1. `tests` (inline) — test code provided in the task config, written into the
     sandbox as `test_file` (default: `test_solution.py`) before running pytest.
  2. `test_file` (path only) — assumes the test file already exists in the sandbox
     (e.g. the model wrote it, or it was pre-seeded).
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

from trajectory_schema import Score as CompactScore

from ..tasks import ScorerConfig

DEFAULT_TEST_FILE = "test_solution.py"


async def score(
    output: str | None,
    target: str | None,
    cfg: ScorerConfig,
    sandbox_dir: Path | None = None,
) -> dict[str, CompactScore]:
    """Run pytest in the sandbox directory and score based on pass/fail."""
    if sandbox_dir is None:
        return {
            "pytest": CompactScore(
                value="I",
                explanation="No sandbox directory available for pytest scorer.",
            )
        }

    test_file = cfg.test_file or DEFAULT_TEST_FILE

    # Write inline tests into the sandbox
    if cfg.tests:
        test_path = sandbox_dir / test_file
        test_path.write_text(cfg.tests)

    # Check that the test file exists
    if not (sandbox_dir / test_file).exists():
        return {
            "pytest": CompactScore(
                value="I",
                explanation=f"Test file {test_file} not found in sandbox.",
            )
        }

    try:
        proc = await asyncio.create_subprocess_exec(
            "python", "-m", "pytest", test_file, "-v", "--tb=short", "--no-header",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=sandbox_dir,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        out_text = stdout.decode(errors="replace")
        err_text = stderr.decode(errors="replace")

        # Count results from pytest output
        passed = len(re.findall(r" PASSED", out_text))
        failed = len(re.findall(r" FAILED", out_text))
        errors = len(re.findall(r" ERROR", out_text))
        total = passed + failed + errors

        if proc.returncode == 0:
            value = "C"
            explanation = f"All tests pass ({passed}/{total})."
        elif passed > 0:
            value = "P"
            explanation = f"Partial: {passed}/{total} passed.\n{out_text[-500:]}"
        else:
            value = "I"
            # Include stderr if stdout is unhelpful (e.g. import errors)
            detail = out_text[-500:] if total > 0 else (err_text[-500:] or out_text[-500:])
            explanation = f"Tests failed ({passed}/{total} passed).\n{detail}"

        return {
            "pytest": CompactScore(
                value=value,
                answer=output,
                explanation=explanation,
                metadata={"passed": passed, "failed": failed, "errors": errors, "total": total},
            )
        }
    except asyncio.TimeoutError:
        return {
            "pytest": CompactScore(
                value="I",
                explanation="Pytest timed out after 30s.",
            )
        }
    except Exception as e:
        return {
            "pytest": CompactScore(
                value="I",
                explanation=f"Scorer error: {e}",
            )
        }
