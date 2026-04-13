/** API client for the trajectory viewer backend. */

import type {
  Trajectory,
  TrajectorySummary,
  RunSummary,
  SearchResponse,
  SearchColumn,
  SearchExample,
} from "@/types/api";

const BASE = "";

async function fetchJSON<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, init);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.error?.message || `HTTP ${res.status}`);
  }
  return res.json();
}

// Trajectories
export const listTrajectories = (params?: {
  limit?: number;
  cursor?: number;
  run_id?: string;
}) => {
  const sp = new URLSearchParams();
  if (params?.limit) sp.set("limit", String(params.limit));
  if (params?.cursor) sp.set("cursor", String(params.cursor));
  if (params?.run_id) sp.set("run_id", params.run_id);
  return fetchJSON<TrajectorySummary[]>(`/api/trajectories?${sp}`);
};

export const getTrajectory = (id: string) =>
  fetchJSON<Trajectory>(`/api/trajectories/${encodeURIComponent(id)}`);

// Runs
export const listRuns = () => fetchJSON<RunSummary[]>("/api/runs");

export const getRun = (id: string) =>
  fetchJSON<{ id: string; task: string; model: string; status: string; sample_count: number; trajectories: TrajectorySummary[] }>(
    `/api/runs/${encodeURIComponent(id)}`,
  );

// Search
export const searchSQL = async (sql: string): Promise<SearchResponse> => {
  const res = await fetch("/api/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sql }),
  });
  const body = await res.json();
  if (!res.ok) {
    throw new Error(body?.error?.message || `HTTP ${res.status}`);
  }
  return body;
};

export const getSearchColumns = () =>
  fetchJSON<SearchColumn[]>("/api/search/columns");

export const getSearchExamples = () =>
  fetchJSON<SearchExample[]>("/api/search/examples");

// Tags
export const addTag = (id: string, tag: string) =>
  fetchJSON<{ status: string }>(`/api/trajectories/${encodeURIComponent(id)}/tags`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tag }),
  });

export const removeTag = (id: string, tag: string) =>
  fetchJSON<{ status: string }>(
    `/api/trajectories/${encodeURIComponent(id)}/tags/${encodeURIComponent(tag)}`,
    { method: "DELETE" },
  );

// Meta
export const getDistinctModels = () => fetchJSON<string[]>("/api/meta/models");
export const getDistinctTags = () => fetchJSON<string[]>("/api/meta/tags");
