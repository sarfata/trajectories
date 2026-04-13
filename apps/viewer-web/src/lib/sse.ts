/** SSE client — subscribes to /api/events and calls handlers. */

export type SSEHandler = (event: string, data: Record<string, unknown>) => void;

export function connectSSE(handler: SSEHandler): () => void {
  const es = new EventSource("/api/events");

  const eventTypes = [
    "trajectory.created",
    "trajectory.updated",
    "trajectory.tagged",
    "trajectory.untagged",
    "run.created",
  ];

  for (const type of eventTypes) {
    es.addEventListener(type, (e: MessageEvent) => {
      try {
        handler(type, JSON.parse(e.data));
      } catch {
        // ignore parse errors
      }
    });
  }

  return () => es.close();
}
