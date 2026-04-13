"""CLI entry point for trajgen."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import tempfile
from pathlib import Path

import click

from .builder import (
    _make_id,
    build_compact_trajectory,
    build_eval_log,
    build_eval_sample,
)
from .executor import run_task
from .scorers import run_scorer
from .sender import post_trajectory, write_trajectory_json
from .tasks import load_tasks
from .tools import Sandbox

logger = logging.getLogger("trajgen")

DEFAULT_MODEL_URL = "http://localhost:1234/v1"
DEFAULT_API_URL = "http://localhost:8000"


def _get_env(name: str, flag_value: str | None, default: str) -> str:
    if flag_value:
        return flag_value
    return os.environ.get(name, default)


@click.group()
@click.option("-v", "--verbose", is_flag=True, help="Enable debug logging.")
def cli(verbose: bool) -> None:
    """trajgen — trajectory generator for coding model evaluation."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-7s %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )


@cli.command()
@click.option("--tasks", "tasks_path", required=True, type=click.Path(exists=True, path_type=Path), help="JSONL tasks file.")
@click.option("--model", "model_name", default=None, help="Model name (e.g. qwen/qwen3-4b-2507).")
@click.option("--model-url", default=None, help="OpenAI-compatible endpoint.")
@click.option("--api", "api_url", default=None, help="Viewer API base URL.")
@click.option("--out", "out_dir", default="./logs", type=click.Path(path_type=Path), help="Output directory.")
@click.option("--concurrency", default=1, type=int, help="Parallel tasks.")
@click.option("--epochs", default=1, type=int, help="Run each task N times (for pass@k stats).")
@click.option("--no-post", is_flag=True, help="Skip POSTing to viewer API.")
def run(
    tasks_path: Path,
    model_name: str | None,
    model_url: str | None,
    api_url: str | None,
    out_dir: Path,
    concurrency: int,
    epochs: int,
    no_post: bool,
) -> None:
    """Run coding tasks through a local LLM and capture trajectories."""
    model = _get_env("TRAJGEN_MODEL", model_name, "qwen/qwen3-4b-2507")
    murl = _get_env("TRAJGEN_MODEL_URL", model_url, DEFAULT_MODEL_URL)
    aurl = _get_env("TRAJGEN_API_URL", api_url, DEFAULT_API_URL)

    task_list = load_tasks(tasks_path)
    click.echo(f"Loaded {len(task_list)} tasks from {tasks_path}")
    click.echo(f"Model: {model} @ {murl}")
    if epochs > 1:
        click.echo(f"Epochs: {epochs} (total runs: {len(task_list) * epochs})")

    run_id = _make_id("run")
    run_dir = out_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    async def process_task(task, epoch: int = 1):
        epoch_label = f" (epoch {epoch}/{epochs})" if epochs > 1 else ""
        click.echo(f"\n--- Task: {task.id}{epoch_label} ---")

        with tempfile.TemporaryDirectory(prefix=f"trajgen_{task.id.replace('/', '_')}_") as tmpdir:
            sandbox = Sandbox(Path(tmpdir))
            result = await run_task(
                task_input=task.input,
                model=model,
                model_url=murl,
                sandbox=sandbox,
            )

            status = "error" if result.error else "success"
            click.echo(f"  Status: {status} | Events: {len(result.events)} | Output: {(result.output or '')[:80]!r}")

            # Score (inside sandbox context so files are still available)
            scores = await run_scorer(result.output, task.target, task.scorer, sandbox_dir=Path(tmpdir))

        if scores:
            for name, s in scores.items():
                click.echo(f"  Score [{name}]: {s.value} — {s.explanation}")

        # Build compact trajectory
        trajectory = build_compact_trajectory(
            task, result, model=model, run_id=run_id, scores=scores,
        )

        # Write to disk (always)
        file_stem = task.id.replace("/", "_")
        if epochs > 1:
            file_stem = f"{file_stem}_epoch{epoch}"
        json_path = run_dir / f"{file_stem}.json"
        write_trajectory_json(trajectory, json_path)

        # Build and write EvalLog
        from inspect_ai.scorer import Score as InspectScore
        inspect_scores = {}
        for name, s in scores.items():
            inspect_scores[name] = InspectScore(
                value=s.value,
                answer=s.answer,
                explanation=s.explanation,
                metadata=s.metadata or {},
            )

        sample = build_eval_sample(task, result, scores=inspect_scores)
        eval_log = build_eval_log(
            sample,
            model=model,
            task_name=task.id.split("/")[0] if "/" in task.id else task.id,
            run_id=run_id,
            started_at=result.started_at,
            completed_at=result.completed_at,
            error_msg=result.error,
        )

        eval_path = run_dir / f"{file_stem}.eval"
        from inspect_ai.log import write_eval_log
        write_eval_log(eval_log, str(eval_path))
        click.echo(f"  Wrote {eval_path}")

        # POST to viewer (fire-and-forget style)
        if not no_post:
            success = await post_trajectory(
                trajectory, api_url=aurl, json_path=json_path, out_dir=out_dir,
            )
            if not success:
                click.echo(f"  Warning: POST failed for {task.id}", err=True)

    # Build list of (task, epoch) pairs
    work_items = [
        (task, epoch)
        for task in task_list
        for epoch in range(1, epochs + 1)
    ]

    async def run_all():
        sem = asyncio.Semaphore(concurrency)

        async def bounded(task, epoch):
            async with sem:
                await process_task(task, epoch)

        await asyncio.gather(*[bounded(t, e) for t, e in work_items])

    asyncio.run(run_all())

    # Summary
    total = len(work_items)
    click.echo(f"\nDone. {total} runs in {run_dir}")
    if epochs > 1:
        _print_pass_at_k_summary(run_dir, task_list, epochs)


def _print_pass_at_k_summary(run_dir: Path, task_list, epochs: int) -> None:
    """Print pass@k summary after a multi-epoch run."""
    import json
    import math

    click.echo("\n=== Pass@k Summary ===")
    click.echo(f"{'Task':<30} {'Pass':>5} {'Fail':>5} {'pass@1':>8}")

    for task in task_list:
        passes = 0
        for epoch in range(1, epochs + 1):
            stem = f"{task.id.replace('/', '_')}_epoch{epoch}"
            json_path = run_dir / f"{stem}.json"
            if not json_path.exists():
                continue
            data = json.loads(json_path.read_text())
            scores = data.get("scores", {})
            # Check any scorer — "C" is pass
            for scorer_name, score in scores.items():
                if score.get("value") == "C":
                    passes += 1
                    break

        n = epochs
        c = passes
        # pass@1 = 1 - C(n-c, 1) / C(n, 1) = c / n
        pass_at_1 = c / n if n > 0 else 0.0
        click.echo(f"{task.id:<30} {c:>5} {n - c:>5} {pass_at_1:>7.0%}")

    click.echo()


@cli.command()
@click.option("--fixtures", "fixture_glob", required=True, help="Glob pattern for fixture JSON files.")
@click.option("--speed", default=1.0, type=float, help="Speed multiplier (higher = faster).")
@click.option("--api", "api_url", default=None, help="Viewer API base URL.")
def replay(fixture_glob: str, speed: float, api_url: str | None) -> None:
    """Replay fixture trajectories to the viewer API with synthetic delays."""
    import glob as glob_mod

    aurl = _get_env("TRAJGEN_API_URL", api_url, DEFAULT_API_URL)
    files = sorted(glob_mod.glob(fixture_glob))
    if not files:
        click.echo(f"No files matched: {fixture_glob}", err=True)
        raise SystemExit(1)

    click.echo(f"Replaying {len(files)} fixtures to {aurl} (speed={speed}x)")

    async def replay_all():
        from trajectory_schema import TrajectoryCreate

        for fpath in files:
            try:
                data = json.loads(Path(fpath).read_text())
                traj = TrajectoryCreate(**data)
                click.echo(f"  Sending {traj.id} ({traj.task_id})...")
                await post_trajectory(traj, api_url=aurl)

                # Synthetic delay based on event count
                delay = max(0.5, len(traj.events) * 0.3) / speed
                await asyncio.sleep(delay)
            except Exception as e:
                click.echo(f"  Error replaying {fpath}: {e}", err=True)

    asyncio.run(replay_all())
    click.echo("Replay complete.")


@cli.command()
@click.option("--log", "log_path", required=True, type=click.Path(exists=True, path_type=Path), help="EvalLog file to push.")
@click.option("--api", "api_url", default=None, help="Viewer API base URL.")
def push(log_path: Path, api_url: str | None) -> None:
    """Upload an existing EvalLog file to the viewer."""
    aurl = _get_env("TRAJGEN_API_URL", api_url, DEFAULT_API_URL)
    url = f"{aurl.rstrip('/')}/api/ingest/evallog"

    click.echo(f"Pushing {log_path} to {url}")

    async def do_push():
        async with httpx.AsyncClient(timeout=60.0) as client:
            import httpx as _httpx

            with open(log_path, "rb") as f:
                resp = await client.post(
                    url,
                    files={"file": (log_path.name, f)},
                )
            if resp.status_code < 400:
                click.echo(f"Uploaded successfully: {resp.status_code}")
                click.echo(resp.text[:500])
            else:
                click.echo(f"Upload failed: {resp.status_code}", err=True)
                click.echo(resp.text[:500], err=True)
                raise SystemExit(1)

    asyncio.run(do_push())
