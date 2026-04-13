import { useQuery } from "@tanstack/react-query";
import { getTrajectory } from "@/lib/api";
import { EventTimeline } from "@/components/EventTimeline";
import { TagChips } from "@/components/TagChips";
import { VerdictBadge } from "@/components/VerdictBadge";
import {
  formatTimestamp,
  formatDuration,
  formatTokens,
  statusColor,
} from "@/lib/format";
import { useState } from "react";

interface DetailPageProps {
  id: string;
  onBack: () => void;
}

export function DetailPage({ id, onBack }: DetailPageProps) {
  const { data: traj, isLoading, error } = useQuery({
    queryKey: ["trajectory", id],
    queryFn: () => getTrajectory(id),
  });

  const [inputExpanded, setInputExpanded] = useState(false);

  if (isLoading) {
    return (
      <div className="p-8 text-center text-zinc-500">Loading trajectory...</div>
    );
  }

  if (error || !traj) {
    return (
      <div className="p-8 text-center text-red-400">
        {error ? String(error) : "Not found"}
      </div>
    );
  }

  return (
    <div className="flex h-full">
      {/* Main pane */}
      <div className="flex-1 min-w-0 overflow-auto">
        {/* Header */}
        <div className="sticky top-0 z-10 bg-zinc-950 border-b border-zinc-800 p-4 space-y-3">
          <div className="flex items-center gap-3">
            <button
              onClick={onBack}
              className="text-sm text-zinc-400 hover:text-zinc-200"
            >
              &larr; Back
            </button>
            <h1 className="text-lg font-mono text-zinc-200 truncate">
              {traj.id}
            </h1>
            <span className={`text-sm ${statusColor(traj.status)}`}>
              {traj.status}
            </span>
            <VerdictBadge verdict={traj.eval_verdict} />
          </div>

          {/* System prompt — collapsed by default */}
          {(() => {
            const systemMsg = traj.messages.find((m) => m.role === "system");
            const promptText = systemMsg?.content || traj.input;
            if (!promptText) return null;
            const label = systemMsg ? "System prompt" : "Input";
            return (
              <>
                <button
                  onClick={() => setInputExpanded(!inputExpanded)}
                  className="flex items-center gap-2 text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
                >
                  <span className="text-zinc-600">
                    {inputExpanded ? "▾" : "▸"}
                  </span>
                  <span className="uppercase tracking-wider">{label}</span>
                  {!inputExpanded && (
                    <span className="text-zinc-600 font-normal truncate max-w-md">
                      {promptText.slice(0, 80)}
                      {promptText.length > 80 && "…"}
                    </span>
                  )}
                </button>
                {inputExpanded && (
                  <div className="bg-zinc-900 rounded-lg p-3 text-sm text-zinc-300">
                    <div className="whitespace-pre-wrap">{promptText}</div>
                  </div>
                )}
              </>
            );
          })()}

          {/* Meta chips */}
          <div className="flex flex-wrap gap-2 text-xs">
            <span className="px-2 py-1 bg-zinc-800 rounded text-zinc-400">
              {traj.model}
            </span>
            {traj.task_id && (
              <span className="px-2 py-1 bg-zinc-800 rounded text-zinc-400">
                {traj.task_id}
              </span>
            )}
            <span className="px-2 py-1 bg-zinc-800 rounded text-zinc-400">
              {formatDuration(traj.duration_ms)}
            </span>
            <span className="px-2 py-1 bg-zinc-800 rounded text-zinc-400">
              {formatTokens(traj.total_tokens)} tokens
            </span>
            <span className="px-2 py-1 bg-zinc-800 rounded text-zinc-400">
              {traj.step_count} steps
            </span>
            <span className="px-2 py-1 bg-zinc-800 rounded text-zinc-400">
              {traj.tool_call_count} tool calls
            </span>
            {traj.compaction_count > 0 && (
              <span className="px-2 py-1 bg-purple-950 rounded text-purple-400">
                {traj.compaction_count} compactions
              </span>
            )}
          </div>

          <TagChips trajectoryId={traj.id} tags={traj.tags} />
        </div>

        {/* Event timeline */}
        <div className="p-4">
          <EventTimeline events={traj.events} scores={traj.scores} />
        </div>

        {/* Output */}
        {traj.output && (
          <div className="p-4 border-t border-zinc-800">
            <div className="text-xs text-zinc-500 mb-2 uppercase tracking-wider">
              Output
            </div>
            <div className="bg-zinc-900 rounded-lg p-3 text-sm text-zinc-300 whitespace-pre-wrap">
              {traj.output}
            </div>
          </div>
        )}
      </div>

      {/* Right sidebar */}
      <div className="w-64 flex-shrink-0 border-l border-zinc-800 p-4 space-y-4 overflow-y-auto">
        <div>
          <div className="text-xs text-zinc-500 uppercase tracking-wider mb-2">
            Metadata
          </div>
          <dl className="space-y-1.5 text-xs">
            <div className="flex justify-between">
              <dt className="text-zinc-500">Started</dt>
              <dd className="text-zinc-300">
                {formatTimestamp(traj.started_at)}
              </dd>
            </div>
            {traj.completed_at && (
              <div className="flex justify-between">
                <dt className="text-zinc-500">Completed</dt>
                <dd className="text-zinc-300">
                  {formatTimestamp(traj.completed_at)}
                </dd>
              </div>
            )}
            {traj.harness && (
              <div className="flex justify-between">
                <dt className="text-zinc-500">Harness</dt>
                <dd className="text-zinc-300">{traj.harness}</dd>
              </div>
            )}
            {traj.run_id && (
              <div className="flex justify-between">
                <dt className="text-zinc-500">Run</dt>
                <dd className="text-zinc-300 font-mono truncate max-w-[140px]">
                  {traj.run_id}
                </dd>
              </div>
            )}
          </dl>
        </div>

        {Object.keys(traj.scores).length > 0 && (
          <div>
            <div className="text-xs text-zinc-500 uppercase tracking-wider mb-2">
              Scores
            </div>
            <div className="space-y-3">
              {Object.entries(traj.scores).map(([name, score]) => {
                const val = score.value;
                const isPass = val === "C" || val === "pass";
                const isFail = val === "I" || val === "fail";
                const borderColor = isPass
                  ? "border-emerald-700"
                  : isFail
                    ? "border-red-700"
                    : "border-zinc-700";

                return (
                  <div
                    key={name}
                    className={`rounded-lg border ${borderColor} bg-zinc-900 p-3 space-y-2`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-medium text-zinc-200">
                        {name}
                      </span>
                      <span
                        className={`text-xs font-mono font-semibold ${
                          isPass
                            ? "text-emerald-400"
                            : isFail
                              ? "text-red-400"
                              : "text-zinc-300"
                        }`}
                      >
                        {typeof val === "object"
                          ? Object.entries(val)
                              .map(([k, v]) => `${k}: ${v}`)
                              .join(", ")
                          : String(val)}
                      </span>
                    </div>
                    {typeof val === "object" && (
                      <div className="space-y-1">
                        {Object.entries(val).map(([dim, v]) => (
                          <div key={dim} className="flex items-center gap-2">
                            <span className="text-xs text-zinc-500 w-20 truncate">
                              {dim}
                            </span>
                            <div className="flex-1 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                              <div
                                className="h-full bg-indigo-500 rounded-full"
                                style={{ width: `${(v as number) * 100}%` }}
                              />
                            </div>
                            <span className="text-xs text-zinc-400 w-8 text-right">
                              {(v as number).toFixed(1)}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                    {score.explanation && (
                      <p className="text-xs text-zinc-400 leading-relaxed">
                        {score.explanation}
                      </p>
                    )}
                    {score.metadata &&
                      Object.keys(score.metadata).length > 0 && (
                        <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs">
                          {Object.entries(score.metadata).map(([k, v]) => (
                            <span key={k} className="text-zinc-500">
                              {k}:{" "}
                              <span className="text-zinc-300">
                                {String(v)}
                              </span>
                            </span>
                          ))}
                        </div>
                      )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {traj.target && (
          <div>
            <div className="text-xs text-zinc-500 uppercase tracking-wider mb-2">
              Target
            </div>
            <pre className="text-xs text-zinc-400 bg-zinc-900 rounded p-2 overflow-auto max-h-40">
              {traj.target}
            </pre>
          </div>
        )}

        {traj.metadata && Object.keys(traj.metadata).length > 0 && (
          <div>
            <div className="text-xs text-zinc-500 uppercase tracking-wider mb-2">
              Extra
            </div>
            <pre className="text-xs text-zinc-400 bg-zinc-900 rounded p-2 overflow-auto max-h-60">
              {JSON.stringify(traj.metadata, null, 2)}
            </pre>
          </div>
        )}

        {traj.error && (
          <div>
            <div className="text-xs text-red-500 uppercase tracking-wider mb-2">
              Error
            </div>
            <pre className="text-xs text-red-300 bg-red-950/50 rounded p-2 overflow-auto max-h-40">
              {traj.error}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
