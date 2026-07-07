import type { NodeType } from "./types";

export interface NodeMeta {
  color: string;
  group: string;
  icon?: string;
}

// Fallback matching backend _NODE_META (schema.py). Used when API is unreachable.
export const FALLBACK_NODE_META: Record<NodeType, NodeMeta> = {
  Sequential: { color: "#6b7280", group: "control", icon: "ListOrdered" },
  Parallel: { color: "#6b7280", group: "control", icon: "Columns" },
  Loop: { color: "#6b7280", group: "control", icon: "Repeat" },
  Branch: { color: "#6b7280", group: "control", icon: "GitBranch" },
  HITL: { color: "#eab308", group: "control", icon: "🔶" },
  LLM: { color: "#3b82f6", group: "leaf", icon: "MessageSquare" },
  Tool: { color: "#22c55e", group: "leaf", icon: "Wrench" },
  Research: { color: "#6366f1", group: "leaf", icon: "Search" },
  Execution: { color: "#f97316", group: "leaf", icon: "Terminal" },
  Coordinator: { color: "#a855f7", group: "dynamic", icon: "🟣" },
  Memory: { color: "#0ea5e9", group: "state", icon: "📦" },
  Subworkflow: { color: "#0ea5e9", group: "state", icon: "🔗" },
  Knowledge: { color: "#14b8a6", group: "retrieval", icon: "📚" },
};

export function mergeMeta(server: Partial<Record<NodeType, NodeMeta>>): Record<NodeType, NodeMeta> {
  return { ...FALLBACK_NODE_META, ...server };
}
