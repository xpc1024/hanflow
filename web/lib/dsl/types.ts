// Mirrors the Python WorkflowDSL (hanflow/core/dsl.py).
// Kept in sync manually in Phase 12; auto-generated from /api/schema/dsl later.

export type NodeType =
  | "Sequential" | "Parallel" | "Loop" | "Branch" | "HITL"
  | "LLM" | "Tool" | "Research" | "Execution"
  | "Coordinator"
  | "Memory" | "Subworkflow"
  | "Knowledge";

export interface WorkflowNode {
  id: string;
  type: NodeType;
  depends_on?: string[];
  config?: Record<string, unknown>;
  condition?: string | null;
  on_error?: Record<string, unknown>;
  retry?: Record<string, unknown> | null;
  timeout_seconds?: number | null;
  sensitivity?: "public" | "internal" | "confidential" | "restricted";
}

export interface WorkflowDSL {
  name: string;
  version?: string;
  description?: string;
  inputs?: Record<string, unknown>;
  nodes: WorkflowNode[];
  outputs?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}
