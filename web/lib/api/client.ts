// API client for the Hanflow backend (Phase 11 endpoints).
// All calls go to /api/* on the same origin (Next.js proxy or CORS).

export interface RunSummary {
  run_id: string;
  status: string;
  result: Record<string, unknown> | null;
}

export interface NodeSchema {
  node_type: string;
  config_schema: Record<string, string>;
  default_config: Record<string, unknown>;
  visual: { color: string; group: string; icon?: string; label?: string };
}

const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${BASE}${path}`);
  if (!r.ok) throw new Error(`${r.status} ${path}`);
  return r.json();
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`${r.status} ${path}`);
  return r.json();
}

export const api = {
  listRuns: () => get<RunSummary[]>("/api/runs"),
  getRun: (id: string) => get<RunSummary>(`/api/runs/${id}`),
  postRun: (yaml: string, inputs: Record<string, unknown> = {}) =>
    post<{ run_id: string; status: string }>("/api/runs", { yaml, inputs }),
  cancelRun: (id: string) =>
    fetch(`${BASE}/api/runs/${id}`, { method: "DELETE" }).then((r) => r.json()),
  getDslSchema: () => get<Record<string, unknown>>("/api/schema/dsl"),
  getNodeSchema: (type: string) => get<NodeSchema>(`/api/schema/node/${type}`),
  validateWorkflow: (yaml: string) =>
    post<{ valid: boolean; error?: string }>("/api/workflows/validate", { yaml }),
  listPendingHitl: () =>
    get<{ run_id: string; payload: Record<string, unknown> | null }[]>("/api/hitl/pending"),
  approveHitl: (runId: string, decidedBy: string) =>
    post<{ run_id: string; status: string }>(`/api/runs/${runId}/approve`, {
      decided_by: decidedBy,
    }),
  wsUrl: (runId: string) => {
    const wsBase = BASE.replace(/^http/, "ws") || `ws://${window.location.host}`;
    return `${wsBase}/api/runs/${runId}/stream`;
  },
};
