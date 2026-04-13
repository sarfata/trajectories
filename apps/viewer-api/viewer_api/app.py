"""FastAPI application — trajectory viewer API."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import db
from .routes import events, meta, runs, search, trajectories


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_path = os.environ.get("DATABASE_URL", "data/viewer.db")
    if db_path.startswith("sqlite:///"):
        db_path = db_path[len("sqlite:///"):]
    await db.init(db_path)
    yield
    await db.close()


app = FastAPI(
    title="Trajectory Viewer",
    description="Browse coding-model trajectories live during training/eval runs. Inspect AI compatible.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(trajectories.router)
app.include_router(runs.router)
app.include_router(search.router)
app.include_router(events.router)
app.include_router(meta.router)

# Serve static frontend if built
static_dir = Path(__file__).resolve().parent.parent.parent / "viewer-web" / "dist"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
