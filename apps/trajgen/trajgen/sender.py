"""POST trajectories to the viewer API, manage sent/send-failed directories."""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path

import httpx

from trajectory_schema import TrajectoryCreate

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAYS = [1.0, 3.0, 10.0]


async def post_trajectory(
    trajectory: TrajectoryCreate,
    *,
    api_url: str,
    json_path: Path | None = None,
    out_dir: Path | None = None,
) -> bool:
    """POST a compact trajectory to the viewer API.

    On success: moves json_path to out_dir/sent/
    On failure: moves json_path to out_dir/send-failed/

    Returns True if POST succeeded.
    """
    url = f"{api_url.rstrip('/')}/api/trajectories"
    payload = trajectory.model_dump(mode="json", exclude_none=True)
    success = False

    async with httpx.AsyncClient(timeout=30.0) as client:
        for attempt in range(MAX_RETRIES):
            try:
                resp = await client.post(url, json=payload)
                if resp.status_code < 400:
                    logger.info("Posted %s -> %d", trajectory.id, resp.status_code)
                    success = True
                    break
                elif resp.status_code < 500:
                    # 4xx — don't retry
                    logger.error(
                        "POST %s failed with %d: %s",
                        trajectory.id,
                        resp.status_code,
                        resp.text[:200],
                    )
                    break
                else:
                    logger.warning(
                        "POST %s got %d (attempt %d/%d)",
                        trajectory.id,
                        resp.status_code,
                        attempt + 1,
                        MAX_RETRIES,
                    )
            except httpx.HTTPError as e:
                logger.warning(
                    "POST %s network error (attempt %d/%d): %s",
                    trajectory.id,
                    attempt + 1,
                    MAX_RETRIES,
                    e,
                )

            if attempt < MAX_RETRIES - 1:
                import asyncio
                await asyncio.sleep(RETRY_DELAYS[attempt])

    # Move the JSON file
    if json_path and out_dir and json_path.exists():
        if success:
            dest = out_dir / "sent"
        else:
            dest = out_dir / "send-failed"
        dest.mkdir(parents=True, exist_ok=True)
        shutil.move(str(json_path), str(dest / json_path.name))
        logger.info("Moved %s -> %s/", json_path.name, dest.name)

    return success


def write_trajectory_json(trajectory: TrajectoryCreate, path: Path) -> Path:
    """Write compact trajectory JSON to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = trajectory.model_dump(mode="json", exclude_none=True)
    path.write_text(json.dumps(data, indent=2))
    logger.info("Wrote %s", path)
    return path
