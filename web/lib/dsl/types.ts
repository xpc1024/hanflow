// Mirrors Python WorkflowDSL (hanflow/core/dsl.py).
// Full field carrying for round-trip (spec Phase 12 §3.3).

export type NodeType =
  | "Sequential" | "Parallel" | "Loop" | "Branch" | "HITL"
  | "LLM" | "Tool" | "Research" | "Execution"
  | "Coordinator"
  | "Memory" | "Subworkflow" | "Knowledge";

export type SensitivityLevel = "public" | "internal" | "confidential" | "restricted";

export interface WorkflowNode {
  id: string;
  type: NodeType;
  depends_on?: string[];
  config?: Record<string, unknown>;
  condition?: string | null;
  on_error?: Record<string, unknown>;
  retry?: Record<string, unknown> | null;
  timeout_seconds?: number | null;
  sensitivity?: SensitivityLevel;
  disabled?: boolean;
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
