import { useState, useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { listTrajectories, searchSQL, getDistinctModels } from "@/lib/api";
import type { TrajectorySummary, SearchResponse } from "@/types/api";
import { SqlEditor } from "@/components/SqlEditor";
import { VerdictBadge } from "@/components/VerdictBadge";
import {
  formatTimestamp,
  formatDuration,
  formatTokens,
  statusColor,
} from "@/lib/format";

interface ListPageProps {
  onSelect: (id: string) => void;
  onSelectRun: (id: string) => void;
}

export function ListPage({ onSelect, onSelectRun }: ListPageProps) {
  const qc = useQueryClient();
  const [searchError, setSearchError] = useState<string | null>(null);
  const [searchResults, setSearchResults] = useState<SearchResponse | null>(
    null,
  );
  const [searchActive, setSearchActive] = useState(false);
  const [filterModel, setFilterModel] = useState<string>("");
  const [filterVerdict, setFilterVerdict] = useState<string>("");

  const { data: trajectories, isLoading } = useQuery({
    queryKey: ["trajectories"],
    queryFn: () => listTrajectories({ limit: 100 }),
  });

  const { data: models } = useQuery({
    queryKey: ["models"],
    queryFn: getDistinctModels,
    staleTime: 60_000,
  });

  const handleSearch = useCallback(async (sql: string) => {
    setSearchError(null);
    setSearchActive(true);
    setSearchResults(null);
    try {
      const res = await searchSQL(sql);
      setSearchResults(res);
    } catch (e: any) {
      setSearchError(e.message);
    }
  }, []);

  const filtered = (trajectories ?? []).filter((t) => {
    if (filterModel && t.model !== filterModel) return false;
    if (filterVerdict && t.eval_verdict !== filterVerdict) return false;
    return true;
  });

  return (
    <div className="flex h-full">
      {/* Left rail — filters */}
      <div className="w-52 flex-shrink-0 border-r border-zinc-800 p-4 space-y-4 overflow-y-auto">
        <div>
          <label className="text-xs text-zinc-500 uppercase tracking-wider block mb-1.5">
            Model
          </label>
          <select
            value={filterModel}
            onChange={(e) => setFilterModel(e.target.value)}
            className="w-full text-sm bg-zinc-900 border border-zinc-700 rounded px-2 py-1.5 text-zinc-300 focus:outline-none focus:border-indigo-500"
          >
            <option value="">All models</option>
            {models?.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-xs text-zinc-500 uppercase tracking-wider block mb-1.5">
            Verdict
          </label>
          <div className="flex flex-wrap gap-1">
            {["", "pass", "fail", "partial"].map((v) => (
              <button
                key={v}
                onClick={() => setFilterVerdict(v)}
                className={`px-2 py-1 text-xs rounded border ${
                  filterVerdict === v
                    ? "border-indigo-500 bg-indigo-950 text-indigo-300"
                    : "border-zinc-700 text-zinc-400 hover:border-zinc-600"
                }`}
              >
                {v || "All"}
              </button>
            ))}
          </div>
        </div>
        <div className="pt-4 border-t border-zinc-800">
          <div className="text-xs text-zinc-600">
            {filtered.length} trajectories
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 min-w-0 flex flex-col">
        {/* Search bar */}
        <div className="p-4 border-b border-zinc-800">
          <SqlEditor onSubmit={handleSearch} error={searchError} />
        </div>

        {/* Results */}
        <div className="flex-1 overflow-auto">
          {searchActive ? (
            searchResults ? (
              <SearchResultsTable
                results={searchResults}
                onClear={() => { setSearchResults(null); setSearchActive(false); setSearchError(null); }}
                onSelect={onSelect}
              />
            ) : searchError ? (
              <div className="p-6 text-center">
                <button
                  onClick={() => { setSearchActive(false); setSearchError(null); }}
                  className="text-xs text-indigo-400 hover:text-indigo-300"
                >
                  Back to list
                </button>
              </div>
            ) : (
              <div className="p-8 text-center text-zinc-500">Running query...</div>
            )
          ) : isLoading ? (
            <div className="p-8 text-center text-zinc-500">Loading...</div>
          ) : (
            <TrajectoryTable
              items={filtered}
              onSelect={onSelect}
              onSelectRun={onSelectRun}
            />
          )}
        </div>
      </div>
    </div>
  );
}

function TrajectoryTable({
  items,
  onSelect,
  onSelectRun,
}: {
  items: TrajectorySummary[];
  onSelect: (id: string) => void;
  onSelectRun: (id: string) => void;
}) {
  return (
    <table className="w-full text-sm">
      <thead className="sticky top-0 bg-zinc-950 border-b border-zinc-800">
        <tr className="text-left text-xs text-zinc-500 uppercase tracking-wider">
          <th className="px-4 py-2.5">Time</th>
          <th className="px-4 py-2.5">Task</th>
          <th className="px-4 py-2.5">Model</th>
          <th className="px-4 py-2.5">Status</th>
          <th className="px-4 py-2.5 text-right">Steps</th>
          <th className="px-4 py-2.5 text-right">Tools</th>
          <th className="px-4 py-2.5 text-right">Tokens</th>
          <th className="px-4 py-2.5">Verdict</th>
          <th className="px-4 py-2.5 text-right">Score</th>
          <th className="px-4 py-2.5">Tags</th>
        </tr>
      </thead>
      <tbody>
        {items.map((t) => (
          <tr
            key={t.id}
            onClick={() => onSelect(t.id)}
            className="border-b border-zinc-800/50 hover:bg-zinc-900 cursor-pointer transition-colors"
          >
            <td className="px-4 py-2.5 text-zinc-400 whitespace-nowrap text-xs">
              {formatTimestamp(t.started_at)}
            </td>
            <td className="px-4 py-2.5 font-mono text-xs text-zinc-300 max-w-[200px] truncate">
              {t.task_id || t.task || "—"}
            </td>
            <td className="px-4 py-2.5 text-xs text-zinc-300">
              {t.model}
            </td>
            <td className={`px-4 py-2.5 text-xs ${statusColor(t.status)}`}>
              {t.status}
            </td>
            <td className="px-4 py-2.5 text-right text-xs text-zinc-400">
              {t.step_count}
            </td>
            <td className="px-4 py-2.5 text-right text-xs text-zinc-400">
              {t.tool_call_count}
            </td>
            <td className="px-4 py-2.5 text-right text-xs text-zinc-400">
              {formatTokens(t.total_tokens)}
            </td>
            <td className="px-4 py-2.5">
              <VerdictBadge verdict={t.eval_verdict} />
            </td>
            <td className="px-4 py-2.5 text-right text-xs font-mono text-zinc-300">
              {t.eval_score != null ? t.eval_score.toFixed(2) : "—"}
            </td>
            <td className="px-4 py-2.5">
              <div className="flex gap-1">
                {t.tags.map((tag) => (
                  <span
                    key={tag}
                    className="px-1.5 py-0.5 text-xs bg-zinc-800 rounded text-zinc-400"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function SearchResultsTable({
  results,
  onClear,
  onSelect,
}: {
  results: SearchResponse;
  onClear: () => void;
  onSelect: (id: string) => void;
}) {
  return (
    <div>
      <div className="flex items-center gap-3 px-4 py-2 border-b border-zinc-800 bg-zinc-900/50">
        <span className="text-xs text-zinc-400">
          {results.rows.length} results in {results.took_ms.toFixed(0)}ms
          {results.truncated && " (truncated at 500)"}
        </span>
        <button
          onClick={onClear}
          className="text-xs text-indigo-400 hover:text-indigo-300"
        >
          Clear search
        </button>
      </div>
      <div className="overflow-auto">
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-zinc-950 border-b border-zinc-800">
            <tr className="text-left text-xs text-zinc-500 uppercase tracking-wider">
              {results.columns.map((c) => (
                <th key={c} className="px-4 py-2">
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {results.rows.map((row, i) => (
              <tr
                key={i}
                className="border-b border-zinc-800/50 hover:bg-zinc-900 cursor-pointer"
                onClick={() => {
                  const id = row.id as string | undefined;
                  if (id) onSelect(id);
                }}
              >
                {results.columns.map((c) => (
                  <td
                    key={c}
                    className="px-4 py-2 text-xs text-zinc-300 max-w-[300px] truncate"
                  >
                    {row[c] != null ? String(row[c]) : "—"}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
