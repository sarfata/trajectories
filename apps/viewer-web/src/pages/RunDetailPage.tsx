import { useQuery } from "@tanstack/react-query";
import { getRun } from "@/lib/api";
import { VerdictBadge } from "@/components/VerdictBadge";
import { formatTimestamp, formatTokens, statusColor } from "@/lib/format";

interface RunDetailPageProps {
  id: string;
  onBack: () => void;
  onSelectTrajectory: (id: string) => void;
}

export function RunDetailPage({ id, onBack, onSelectTrajectory }: RunDetailPageProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["run", id],
    queryFn: () => getRun(id),
  });

  if (isLoading) {
    return <div className="p-8 text-center text-zinc-500">Loading run...</div>;
  }

  if (error || !data) {
    return (
      <div className="p-8 text-center text-red-400">
        {error ? String(error) : "Not found"}
      </div>
    );
  }

  const verdictCounts = (data.trajectories ?? []).reduce(
    (acc, t) => {
      const v = t.eval_verdict || "none";
      acc[v] = (acc[v] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>,
  );

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <button
          onClick={onBack}
          className="text-sm text-zinc-400 hover:text-zinc-200"
        >
          &larr; Back
        </button>
        <h1 className="text-lg font-mono text-zinc-200">{data.id}</h1>
        <span className={`text-sm ${statusColor(data.status || "")}`}>
          {data.status}
        </span>
      </div>

      <div className="flex gap-6 text-sm">
        <div>
          <span className="text-zinc-500">Task:</span>{" "}
          <span className="text-zinc-300">{data.task || "—"}</span>
        </div>
        <div>
          <span className="text-zinc-500">Model:</span>{" "}
          <span className="text-zinc-300">{data.model || "—"}</span>
        </div>
        <div>
          <span className="text-zinc-500">Samples:</span>{" "}
          <span className="text-zinc-300">{data.sample_count}</span>
        </div>
      </div>

      {/* Verdict summary */}
      <div className="flex gap-3">
        {Object.entries(verdictCounts).map(([v, n]) => (
          <div
            key={v}
            className="px-3 py-2 bg-zinc-900 rounded-lg border border-zinc-800 text-center"
          >
            <div className="text-lg font-mono text-zinc-200">{n}</div>
            <div className="text-xs text-zinc-500">{v}</div>
          </div>
        ))}
      </div>

      {/* Trajectory list */}
      <table className="w-full text-sm">
        <thead className="border-b border-zinc-800">
          <tr className="text-left text-xs text-zinc-500 uppercase tracking-wider">
            <th className="px-4 py-2">Task ID</th>
            <th className="px-4 py-2">Status</th>
            <th className="px-4 py-2 text-right">Steps</th>
            <th className="px-4 py-2 text-right">Tokens</th>
            <th className="px-4 py-2">Verdict</th>
            <th className="px-4 py-2 text-right">Score</th>
          </tr>
        </thead>
        <tbody>
          {(data.trajectories ?? []).map((t) => (
            <tr
              key={t.id}
              onClick={() => onSelectTrajectory(t.id)}
              className="border-b border-zinc-800/50 hover:bg-zinc-900 cursor-pointer"
            >
              <td className="px-4 py-2 font-mono text-xs text-zinc-300">
                {t.task_id || t.id}
              </td>
              <td className={`px-4 py-2 text-xs ${statusColor(t.status)}`}>
                {t.status}
              </td>
              <td className="px-4 py-2 text-right text-xs text-zinc-400">
                {t.step_count}
              </td>
              <td className="px-4 py-2 text-right text-xs text-zinc-400">
                {formatTokens(t.total_tokens)}
              </td>
              <td className="px-4 py-2">
                <VerdictBadge verdict={t.eval_verdict} />
              </td>
              <td className="px-4 py-2 text-right text-xs font-mono text-zinc-300">
                {t.eval_score != null ? t.eval_score.toFixed(2) : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
