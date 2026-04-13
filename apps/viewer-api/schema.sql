-- Trajectory viewer schema — SQLite with WAL mode.

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS runs (
  id            TEXT PRIMARY KEY,
  task          TEXT,
  model         TEXT,
  created_at    INTEGER,
  status        TEXT,
  stats         TEXT,       -- JSON
  eval_spec     TEXT        -- JSON
);

CREATE TABLE IF NOT EXISTS trajectories (
  id                TEXT PRIMARY KEY,
  run_id            TEXT REFERENCES runs(id) ON DELETE CASCADE,
  task              TEXT,
  task_id           TEXT,
  model             TEXT NOT NULL,
  harness           TEXT,
  status            TEXT NOT NULL,
  started_at        INTEGER NOT NULL,
  completed_at      INTEGER,

  input             TEXT NOT NULL,
  target            TEXT,
  output            TEXT,
  error             TEXT,

  step_count        INTEGER NOT NULL DEFAULT 0,
  tool_call_count   INTEGER NOT NULL DEFAULT 0,
  compaction_count  INTEGER NOT NULL DEFAULT 0,
  total_tokens      INTEGER,
  duration_ms       INTEGER,
  tool_names        TEXT,
  eval_verdict      TEXT,
  eval_score        REAL,

  metadata          TEXT,   -- JSON
  raw_sample        TEXT    -- JSON: original payload for round-trip export
);

CREATE INDEX IF NOT EXISTS idx_traj_started ON trajectories(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_traj_model   ON trajectories(model);
CREATE INDEX IF NOT EXISTS idx_traj_verdict ON trajectories(eval_verdict);
CREATE INDEX IF NOT EXISTS idx_traj_run     ON trajectories(run_id);

CREATE TABLE IF NOT EXISTS events (
  trajectory_id TEXT    NOT NULL REFERENCES trajectories(id) ON DELETE CASCADE,
  idx           INTEGER NOT NULL,
  kind          TEXT    NOT NULL,
  timestamp     INTEGER,
  payload       TEXT    NOT NULL,  -- JSON
  PRIMARY KEY (trajectory_id, idx)
);

CREATE TABLE IF NOT EXISTS scores (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  trajectory_id  TEXT    NOT NULL REFERENCES trajectories(id) ON DELETE CASCADE,
  name           TEXT    NOT NULL,
  value_raw      TEXT    NOT NULL,  -- JSON
  score_numeric  REAL,
  verdict        TEXT,
  answer         TEXT,
  explanation    TEXT,
  metadata       TEXT               -- JSON
);

CREATE TABLE IF NOT EXISTS tags (
  trajectory_id TEXT    NOT NULL REFERENCES trajectories(id) ON DELETE CASCADE,
  tag           TEXT    NOT NULL,
  created_at    INTEGER NOT NULL,
  PRIMARY KEY (trajectory_id, tag)
);

CREATE VIEW IF NOT EXISTS v_trajectories AS
SELECT
  t.id, t.run_id, t.task, t.task_id, t.model, t.harness, t.status,
  t.started_at, t.completed_at, t.duration_ms,
  t.step_count, t.tool_call_count, t.compaction_count,
  t.total_tokens, t.tool_names,
  t.eval_verdict, t.eval_score,
  (SELECT GROUP_CONCAT(tag, ',') FROM tags WHERE trajectory_id = t.id) AS tags,
  (SELECT GROUP_CONCAT(name, ',') FROM scores WHERE trajectory_id = t.id) AS scorers
FROM trajectories t;
