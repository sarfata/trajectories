# Trajectory Viewer — project spec

A small researcher-facing tool for browsing coding-model trajectories live during training/eval runs. Two loosely-coupled apps in a mini monorepo, sharing one schema.

1. **Generator** — runs coding tasks through OpenCode against a local LLM, captures the trajectory as an Inspect AI–compatible `EvalSample`, scores it, and POSTs to the viewer. See [`GENERATOR_SPEC.md`](./GENERATOR_SPEC.md).
2. **Viewer** — FastAPI + SQLite backend with a React + TypeScript + Tailwind frontend. Lists runs live, SQL search, step-by-step inspection, tagging. See [`WEB_UI_SPEC.md`](./WEB_UI_SPEC.md).

Shared data contract: [`TRAJECTORY.md`](./TRAJECTORY.md). Any change there requires coordinating both sides.

## Design principle

**Our trajectory format is a subset of [Inspect AI](https://inspect.aisi.org.uk)'s `EvalLog`.** Files we produce open in `inspect view` unmodified; `.eval` files Inspect produces can be uploaded into our viewer. We don't render every event type Inspect supports, but we refuse to invent parallel field names where theirs already exist. This gives us:

- An off-ramp for the researcher: if they prefer Inspect's viewer for a specific run, one click exports it.
- An on-ramp for existing data: users with existing `.eval` files don't need our generator at all — they just upload.
- A credible claim to interop instead of a snowflake schema.

## Alternative paths

Because our format is Inspect-compatible, two reasonable alternatives exist and should be named up front:

1. **Just use Inspect AI end-to-end.** `inspect eval humaneval --model ollama/kimi-k2` produces `.eval` files; `inspect view` opens them. No custom anything. Good for production.
2. **Use Inspect as the generator, our viewer as the frontend.** Skip writing `apps/trajgen/` entirely; upload `.eval` files to `POST /api/ingest/evallog`. Good if the interesting work for you is the UI.
3. **Build both, which is what this spec describes.** Good as a learning exercise, which is the point here. The generator is intentionally small so we don't accidentally build a worse Inspect.

## Architecture at a glance

```
┌──────────────┐  HTTP POST    ┌────────────────┐
│  Generator   │ ────────────▶ │  Viewer API    │
│  OpenCode +  │               │  (FastAPI)     │
│  local LLM   │               │                │
└──────────────┘               └───────┬────────┘
┌──────────────┐  POST .eval   ┌───────▼────────┐
│ inspect eval │ ────────────▶ │  SQLite file   │
│  (alt path)  │               │                │
└──────────────┘               └───────┬────────┘
                                       │
                                       ▼
                               ┌──────────────┐
                               │  React SPA   │
                               │  SSE + fetch │
                               └──────────────┘
```

### Why this shape

- **SQLite**: single file, no server, ships in a container. Fine for a demo, fine for millions of rows.
- **Viewer owns all writes.** Generator is an HTTP client only. HTTP boundary keeps the two apps independently deployable.
- **SSE, not WebSockets**: one-way, plain HTTP, TanStack Query has clean patterns; we never need client→server pushes.
- **SQL search box** instead of a filter form, per the brief. Safe because the view is read-only and we `sqlglot`-parse before executing.
- **No auth.** Deploy behind a VPN / Tailscale / SSH tunnel.

## Running the demo

Target: one command.

```
make demo
# viewer + replay-mode generator streaming fixture EvalLogs with realistic delays.
# Open http://localhost:8000.
```

## Repo layout — mini monorepo

Single repo, three workspaces, one shared schema package. Two Claude Code instances work in parallel: one owns `apps/trajgen/`, one owns `apps/viewer-api/` + `apps/viewer-web/`. They share `packages/trajectory-schema/` and the ingest endpoints. Changes to the shared schema get a PR both instances review.

```
/
├── README.md                                ← this file
├── docs/
│   ├── TRAJECTORY.md                        ← data contract (shared)
│   ├── GENERATOR_SPEC.md
│   └── WEB_UI_SPEC.md
│
├── packages/
│   └── trajectory-schema/                   ← shared — wraps Inspect's types we use
│       ├── pyproject.toml
│       └── trajectory_schema/
│           ├── __init__.py
│           └── models.py                    ← Trajectory, Event, Score (re-exports Inspect types)
│
├── apps/
│   ├── trajgen/                             ← project 1 (Python, uses inspect_ai as lib)
│   │   ├── pyproject.toml
│   │   ├── trajgen/
│   │   └── fixtures/*.json                  ← seed EvalLogs for replay mode + CI
│   │
│   ├── viewer-api/                          ← project 2a (Python + FastAPI)
│   │   ├── pyproject.toml
│   │   ├── schema.sql
│   │   └── viewer_api/
│   │
│   └── viewer-web/                          ← project 2b (React + TS)
│       ├── package.json
│       └── src/
│
├── Makefile                                 ← make dev, make demo, make test
├── docker-compose.yml
└── .github/workflows/ci.yml
```

### Tooling

- **Python**: `uv` workspaces tie `trajgen`, `viewer-api`, and `trajectory-schema` together. A root `pyproject.toml` declares the workspace; apps have path deps on the schema package. One `uv sync` at the root does everything.
- **TS**: `viewer-web` is a plain Vite app. We generate TS types from the schema package's JSON Schema output so both sides stay in sync without a JS monorepo.
- **CI**: GitHub Actions matrix over the three apps. Changes to `packages/trajectory-schema/` trigger all three. One interop job ingests a fixture `.eval`, exports it, and runs `inspect log convert` to verify round-trip.

## Decisions made

- **Format**: Inspect AI `EvalLog` subset. Ingest and export are bidirectional.
- **Who owns the DB**: the viewer. Generator writes `out/<id>.json` locally too.
- **SSE vs WebSockets**: SSE.
- **Shared models**: one package in the monorepo, importing Inspect types where possible.
- **Models supported**: Kimi K2 and Gemma both. Compare side-by-side in the viewer.
- **Streaming submit (v2 mode)**: specced, deferred. v1 ships batch-submit; runs pop in as they complete.
- **Agent-friendly docs**: `/llms.txt` + `/llms-full.txt` + a carefully filled-out OpenAPI in v1. MCP server later.

## Still worth calling out

- **SQL injection surface on the search box** — read-only SQLite connection, `PRAGMA query_only = ON`, `sqlglot` parsing (single `SELECT` against `v_trajectories`), wrapped `LIMIT 500`, 5 s timeout. Fine for a no-auth researcher tool; revisit if ever exposed to the open internet.
- **Schema verification** — field names in `TRAJECTORY.md` are drawn from Inspect's published docs, not a line-by-line read of their Python dataclasses. The CI interop test (`ingest .eval → export → inspect log convert → diff`) is the real guarantee. The first implementation task should be to pin a specific `inspect_ai` version and import their Pydantic models where we can rather than redeclare.
