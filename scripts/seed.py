"""Seed the viewer database with fixture data."""

import json
import sys
import time
from pathlib import Path

import httpx

API_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
FIXTURES_DIR = Path(__file__).resolve().parent.parent / "apps" / "trajgen" / "fixtures"


def main():
    client = httpx.Client(base_url=API_URL, timeout=10)

    for fixture_path in sorted(FIXTURES_DIR.glob("*.json")):
        print(f"Loading {fixture_path.name}...")
        data = json.loads(fixture_path.read_text())
        trajectories = data if isinstance(data, list) else [data]

        for traj in trajectories:
            try:
                resp = client.post("/api/trajectories", json=traj)
                if resp.status_code == 201:
                    print(f"  + {traj['id']}")
                else:
                    print(f"  ! {traj['id']}: {resp.status_code} {resp.text[:100]}")
            except Exception as e:
                print(f"  ! {traj['id']}: {e}")

    print("Done.")


if __name__ == "__main__":
    main()
