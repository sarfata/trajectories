import { verdictColor } from "@/lib/format";

export function VerdictBadge({ verdict }: { verdict: string | null | undefined }) {
  if (!verdict) return <span className="text-zinc-600">—</span>;
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${verdictColor(verdict)} ${
        verdict === "pass"
          ? "bg-emerald-950"
          : verdict === "fail"
            ? "bg-red-950"
            : "bg-amber-950"
      }`}
    >
      {verdict}
    </span>
  );
}
