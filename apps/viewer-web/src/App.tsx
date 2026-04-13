import { useCallback, useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ListPage } from "@/pages/ListPage";
import { DetailPage } from "@/pages/DetailPage";
import { RunDetailPage } from "@/pages/RunDetailPage";
import { connectSSE } from "@/lib/sse";

type Route =
  | { page: "list" }
  | { page: "detail"; id: string }
  | { page: "run"; id: string };

function parseRoute(): Route {
  const hash = window.location.hash.slice(1);
  if (hash.startsWith("/t/")) return { page: "detail", id: decodeURIComponent(hash.slice(3)) };
  if (hash.startsWith("/r/")) return { page: "run", id: decodeURIComponent(hash.slice(3)) };
  return { page: "list" };
}

export function App() {
  const [route, setRoute] = useState<Route>(parseRoute);
  const qc = useQueryClient();

  useEffect(() => {
    const handleHash = () => setRoute(parseRoute());
    window.addEventListener("hashchange", handleHash);
    return () => window.removeEventListener("hashchange", handleHash);
  }, []);

  // SSE: invalidate queries on events
  useEffect(() => {
    return connectSSE((event) => {
      if (event === "trajectory.created" || event === "trajectory.updated") {
        qc.invalidateQueries({ queryKey: ["trajectories"] });
      }
      if (event === "run.created") {
        qc.invalidateQueries({ queryKey: ["runs"] });
      }
    });
  }, [qc]);

  const navigate = useCallback((r: Route) => {
    if (r.page === "list") window.location.hash = "/";
    else if (r.page === "detail") window.location.hash = `/t/${encodeURIComponent(r.id)}`;
    else window.location.hash = `/r/${encodeURIComponent(r.id)}`;
  }, []);

  return (
    <div className="h-full flex flex-col">
      {/* Minimal header */}
      <header className="flex-shrink-0 h-11 flex items-center px-4 border-b border-zinc-800 bg-zinc-950">
        <button
          onClick={() => navigate({ page: "list" })}
          className="text-sm font-semibold text-zinc-200 hover:text-white tracking-tight"
        >
          Trajectory Viewer
        </button>
        <span className="ml-2 text-xs text-zinc-600">v0.1</span>
      </header>

      {/* Content */}
      <main className="flex-1 min-h-0">
        {route.page === "list" && (
          <ListPage
            onSelect={(id) => navigate({ page: "detail", id })}
            onSelectRun={(id) => navigate({ page: "run", id })}
          />
        )}
        {route.page === "detail" && (
          <DetailPage id={route.id} onBack={() => navigate({ page: "list" })} />
        )}
        {route.page === "run" && (
          <RunDetailPage
            id={route.id}
            onBack={() => navigate({ page: "list" })}
            onSelectTrajectory={(id) => navigate({ page: "detail", id })}
          />
        )}
      </main>
    </div>
  );
}
