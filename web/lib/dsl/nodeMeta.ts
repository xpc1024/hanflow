// Node visual metadata — mirrors the backend /api/schema/node/{type} response
// (hanflow/api/routes/schema.py _NODE_META). Kept in sync manually in Phase 13;
// fetched from the API at runtime in Phase 14+.

import type { NodeType } from "./types";

export interface NodeMeta {
  color: string;
  group: "control" | "leaf" | "dynamic" | "state" | "retrieval";
  icon?: string;
  label: string;
}

export const NODE_META: Record<NodeType, NodeMeta> = {
  Sequential: { color: "#6b7280", group: "control", label: "Sequential" },
  Parallel: { color: "#6b7280", group: "control", label: "Parallel" },
  Loop: { color: "#6b7280", group: "control", label: "Loop" },
  Branch: { color: "#6b7280", group: "control", label: "Branch" },
  HITL: { color: "#eab308", group: "control", icon: "🔶", label: "HITL" },
  LLM: { color: "#3b82f6", group: "leaf", label: "LLM" },
  Tool: { color: "#22c55e", group: "leaf", label: "Tool" },
  Research: { color: "#6366f1", group: "leaf", label: "Research" },
  Execution: { color: "#f97316", group: "leaf", label: "Execution" },
  Coordinator: { color: "#a855f7", group: "dynamic", icon: "🟣", label: "Coordinator" },
  Memory: { color: "#0ea5e9", group: "state", icon: "📦", label: "Memory" },
  Subworkflow: { color: "#0ea5e9", group: "state", icon: "🔗", label: "Subworkflow" },
  Knowledge: { color: "#14b8a6", group: "retrieval", icon: "📚", label: "Knowledge" },
};

// Default config per nodeType — mirrors backend _DEFAULT_CONFIG.
export const DEFAULT_CONFIG: Record<string, Record<string, unknown>> = {
  LLM: { template: "" },
  Tool: { tool: "", args: {} },
  HITL: { actions: ["approve", "edit", "reject", "reroute"] },
  Coordinator: { sub_agents: [], plan_hitl: false, max_iterations: 5 },
  Knowledge: { store: "", query: "", top_k: 5 },
};

// Config field schema per nodeType — mirrors backend _CONFIG_SCHEMA.
// "string" = text input, "integer" = number input, "boolean" = checkbox,
// "array" = list editor, "object" = JSON editor, "any" = JSON editor.
export const CONFIG_SCHEMA: Record<string, Record<string, string>> = {
  LLM: { template: "string", model: "string?" },
  Tool: { tool: "string", args: "object?" },
  HITL: { actions: "array", title: "string?", description: "string?" },
  Coordinator: {
    sub_agents: "array",
    plan_hitl: "boolean?",
    max_iterations: "integer?",
    success_criteria: "string?",
  },
  Knowledge: { store: "string", query: "string", top_k: "integer?" },
  Memory: { action: "string", key: "string", value: "any?" },
};
