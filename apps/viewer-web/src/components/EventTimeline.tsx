import { useState } from "react";
import type { TrajectoryEvent, Score } from "@/types/api";
import { formatDuration, formatTokens } from "@/lib/format";

function ModelEventCard({ event }: { event: TrajectoryEvent }) {
  return (
    <div className="border-l-2 border-blue-500 bg-zinc-900 rounded-r-lg p-4">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs font-medium text-blue-400 uppercase">
          {event.role ?? "assistant"}
        </span>
        {event.usage && (
          <span className="text-xs text-zinc-500 ml-auto">
            {formatTokens(event.usage.input_tokens)} in / {formatTokens(event.usage.output_tokens)} out
          </span>
        )}
      </div>
      <div className="text-sm text-zinc-300 whitespace-pre-wrap break-words">
        {event.output}
      </div>
    </div>
  );
}

function ToolEventCard({ event }: { event: TrajectoryEvent }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="border-l-2 border-amber-500 bg-zinc-900 rounded-r-lg p-4">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 w-full text-left"
      >
        <span className="text-xs font-medium text-amber-400 uppercase">
          tool
        </span>
        <span className="text-sm font-mono text-zinc-200">
          {event.function ?? "unknown"}
        </span>
        {event.duration_ms != null && (
          <span className="text-xs text-zinc-500">
            {formatDuration(event.duration_ms)}
          </span>
        )}
        {event.error && (
          <span className="text-xs text-red-400 ml-2">error</span>
        )}
        <span className="ml-auto text-xs text-zinc-600">
          {expanded ? "▾" : "▸"}
        </span>
      </button>
      {expanded && (
        <div className="mt-3 grid grid-cols-2 gap-3">
          <div>
            <div className="text-xs text-zinc-500 mb-1">Arguments</div>
            <pre className="text-xs text-zinc-400 bg-zinc-950 rounded p-2 overflow-auto max-h-60">
              {JSON.stringify(event.arguments, null, 2)}
            </pre>
          </div>
          <div>
            <div className="text-xs text-zinc-500 mb-1">Result</div>
            <pre className="text-xs text-zinc-400 bg-zinc-950 rounded p-2 overflow-auto max-h-60">
              {event.error
                ? event.error
                : JSON.stringify(event.result, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}

function CompactionEventCard({ event }: { event: TrajectoryEvent }) {
  return (
    <div className="border-l-2 border-purple-500 bg-purple-950/30 rounded-r-lg p-4">
      <div className="flex items-center gap-2">
        <span className="text-xs font-medium text-purple-400 uppercase">
          compaction
        </span>
        <span className="text-xs text-zinc-400">
          {formatTokens(event.before_tokens)} &rarr;{" "}
          {formatTokens(event.after_tokens)}
        </span>
      </div>
      {event.summary && (
        <div className="text-xs text-zinc-500 mt-1">{event.summary}</div>
      )}
    </div>
  );
}

function ScoreEventCard({ event }: { event: TrajectoryEvent }) {
  return (
    <div className="border-l-2 border-emerald-500 bg-zinc-900 rounded-r-lg p-4">
      <div className="flex items-center gap-2">
        <span className="text-xs font-medium text-emerald-400 uppercase">
          score
        </span>
        <span className="text-sm font-mono text-zinc-200">{event.name}</span>
        {event.score && (
          <span className="text-sm text-zinc-300 ml-2">
            {typeof event.score.value === "object"
              ? JSON.stringify(event.score.value)
              : String(event.score.value)}
          </span>
        )}
      </div>
      {event.score?.explanation && (
        <div className="text-xs text-zinc-500 mt-1">
          {event.score.explanation}
        </div>
      )}
    </div>
  );
}

function ErrorEventCard({ event }: { event: TrajectoryEvent }) {
  return (
    <div className="border-l-2 border-red-500 bg-red-950/30 rounded-r-lg p-4">
      <span className="text-xs font-medium text-red-400 uppercase">error</span>
      <div className="text-sm text-red-300 mt-1 whitespace-pre-wrap">
        {event.error || event.output || "Unknown error"}
      </div>
    </div>
  );
}

function InfoEventCard({ event }: { event: TrajectoryEvent }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="border-l-2 border-zinc-600 bg-zinc-900/50 rounded-r-lg px-4 py-2">
      <button
        onClick={() => setExpanded(!expanded)}
        className="text-xs text-zinc-500 hover:text-zinc-400"
      >
        {expanded ? "▾" : "▸"} {event.event}
        {event.summary && `: ${event.summary}`}
      </button>
      {expanded && event.output && (
        <pre className="text-xs text-zinc-500 mt-1">{event.output}</pre>
      )}
    </div>
  );
}

function ScoreSummary({ scores }: { scores: Record<string, Score> }) {
  return (
    <div className="flex flex-wrap gap-2 mt-2">
      {Object.entries(scores).map(([name, s]) => (
        <span
          key={name}
          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-zinc-800 border border-zinc-700 text-xs"
        >
          <span className="text-zinc-400">{name}:</span>
          <span className="text-zinc-200 font-mono">
            {typeof s.value === "object"
              ? JSON.stringify(s.value)
              : String(s.value)}
          </span>
        </span>
      ))}
    </div>
  );
}

const RENDERED_KINDS = new Set([
  "model",
  "tool",
  "compaction",
  "score",
  "error",
  "info",
  "input",
]);

export function EventTimeline({
  events,
  scores,
}: {
  events: TrajectoryEvent[];
  scores?: Record<string, Score>;
}) {
  const hidden = events.filter((e) => !RENDERED_KINDS.has(e.event));

  return (
    <div className="space-y-3">
      {hidden.length > 0 && (
        <div className="text-xs text-zinc-600 px-2">
          {hidden.length} events hidden (
          {[...new Set(hidden.map((e) => e.event))].join(", ")})
        </div>
      )}
      {events.map((event, i) => {
        switch (event.event) {
          case "model":
            return <ModelEventCard key={i} event={event} />;
          case "tool":
            return <ToolEventCard key={i} event={event} />;
          case "compaction":
            return <CompactionEventCard key={i} event={event} />;
          case "score":
            return <ScoreEventCard key={i} event={event} />;
          case "error":
            return <ErrorEventCard key={i} event={event} />;
          case "info":
          case "input":
          case "sample_init":
          case "sample_limit":
            return <InfoEventCard key={i} event={event} />;
          default:
            return null;
        }
      })}
    </div>
  );
}
