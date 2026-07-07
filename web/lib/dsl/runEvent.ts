export interface NodeRunState {
  status: "idle" | "pending" | "running" | "ok" | "error" | "skipped" | "paused";
  outputSummary: string;
  outputFull?: unknown;
  error?: string;
  startedAt?: string;
  endedAt?: string;
  tokens?: number;
}

export interface RunEvent {
  kind: string;
  node_id?: string;
  data: Record<string, any>;
}

export interface LogEntry {
  kind: string;
  node_id?: string;
  message: string;
  count?: number;
}

export function applyRunEvent(
  state: Record<string, NodeRunState>,
  event: RunEvent
): Record<string, NodeRunState> {
  const next = { ...state };
  const id = event.node_id;
  if (!id) return next;
  const node = next[id] ?? { status: "idle" as const, outputSummary: "" };

  switch (event.kind) {
    case "node_start":
      next[id] = { ...node, status: "running", startedAt: new Date().toISOString() };
      break;
    case "node_end": {
      const endStatus = event.data.status;
      const mapped =
        endStatus === "succeeded" ? "ok" :
        endStatus === "failed" ? "error" :
        endStatus === "skipped" ? "skipped" :
        endStatus === "paused" ? "paused" : "ok";
      next[id] = { ...node, status: mapped as NodeRunState["status"], outputFull: event.data.output, endedAt: new Date().toISOString() };
      break;
    }
    case "hitl_paused":
      next[id] = { ...node, status: "paused" };
      break;
    case "hitl_resumed":
      next[id] = { ...node, status: "running" };
      break;
    case "error":
      next[id] = { ...node, status: "error", error: event.data.error };
      break;
  }
  return next;
}

export function mapEventsToLog(events: RunEvent[]): LogEntry[] {
  const log: LogEntry[] = [];
  let tokenBatch: { nodeId: string; count: number } | null = null;

  const flushBatch = () => {
    if (tokenBatch) {
      log.push({ kind: "llm_token_batch", node_id: tokenBatch.nodeId, message: `${tokenBatch.count} tokens`, count: tokenBatch.count });
      tokenBatch = null;
    }
  };

  for (const e of events) {
    if (e.kind === "llm_token") {
      if (tokenBatch && tokenBatch.nodeId !== e.node_id) flushBatch();
      if (!tokenBatch) tokenBatch = { nodeId: e.node_id!, count: 0 };
      tokenBatch.count++;
    } else {
      flushBatch();
      log.push({ kind: e.kind, node_id: e.node_id, message: `${e.kind}${e.data.status ? ": " + e.data.status : ""}` });
    }
  }
  flushBatch();
  return log;
}
