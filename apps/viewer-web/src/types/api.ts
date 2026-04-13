/** API types matching the trajectory-schema Pydantic models. */

export interface TokenUsage {
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
}

export interface Score {
  value: string | number | Record<string, number>;
  answer?: string | null;
  explanation?: string | null;
  metadata?: Record<string, unknown> | null;
}

export interface Message {
  role: string;
  content: string;
  tool_call_id?: string | null;
}

export interface TrajectoryEvent {
  event: string;
  timestamp?: number | null;
  // model
  role?: string | null;
  output?: string | null;
  usage?: TokenUsage | null;
  // tool
  id?: string | null;
  function?: string | null;
  arguments?: unknown;
  result?: unknown;
  error?: string | null;
  duration_ms?: number | null;
  // compaction
  before_tokens?: number | null;
  after_tokens?: number | null;
  summary?: string | null;
  // score
  name?: string | null;
  score?: Score | null;
  // span
  span_id?: string | null;
  span_name?: string | null;
}

export interface TrajectorySummary {
  id: string;
  run_id?: string | null;
  task?: string | null;
  task_id?: string | null;
  model: string;
  harness?: string | null;
  status: string;
  started_at: number;
  completed_at?: number | null;
  duration_ms?: number | null;
  step_count: number;
  tool_call_count: number;
  compaction_count: number;
  total_tokens?: number | null;
  tool_names?: string | null;
  eval_verdict?: string | null;
  eval_score?: number | null;
  tags: string[];
}

export interface Trajectory extends TrajectorySummary {
  input: string;
  target?: string | null;
  output?: string | null;
  error?: string | null;
  messages: Message[];
  events: TrajectoryEvent[];
  scores: Record<string, Score>;
  metadata?: Record<string, unknown> | null;
}

export interface RunSummary {
  id: string;
  task?: string | null;
  model?: string | null;
  created_at?: number | null;
  status?: string | null;
  sample_count: number;
}

export interface SearchResponse {
  columns: string[];
  rows: Record<string, unknown>[];
  took_ms: number;
  truncated: boolean;
}

export interface SearchColumn {
  name: string;
  type: string;
  description: string;
}

export interface SearchExample {
  title: string;
  sql: string;
}

export interface ErrorEnvelope {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
}
