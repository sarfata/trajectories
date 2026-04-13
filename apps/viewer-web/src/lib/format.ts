/** Formatting utilities. */

export function formatTimestamp(ms: number): string {
  return new Date(ms).toLocaleString();
}

export function formatDuration(ms: number | null | undefined): string {
  if (ms == null) return "—";
  if (ms < 1000) return `${ms}ms`;
  const s = ms / 1000;
  if (s < 60) return `${s.toFixed(1)}s`;
  const m = Math.floor(s / 60);
  const rem = Math.round(s % 60);
  return `${m}m ${rem}s`;
}

export function formatTokens(n: number | null | undefined): string {
  if (n == null) return "—";
  if (n < 1000) return String(n);
  if (n < 1_000_000) return `${(n / 1000).toFixed(1)}k`;
  return `${(n / 1_000_000).toFixed(2)}M`;
}

export function verdictColor(v: string | null | undefined): string {
  if (!v) return "text-zinc-400";
  switch (v) {
    case "pass":
      return "text-emerald-400";
    case "fail":
      return "text-red-400";
    case "partial":
      return "text-amber-400";
    default:
      return "text-zinc-400";
  }
}

export function statusColor(s: string): string {
  switch (s) {
    case "success":
      return "text-emerald-400";
    case "error":
      return "text-red-400";
    case "started":
      return "text-blue-400";
    default:
      return "text-zinc-400";
  }
}
