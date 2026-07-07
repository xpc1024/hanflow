import type { WorkflowDSL } from "./types";
import { checkConfig, checkReferences } from "./validate";
import { getSchema, FALLBACK_SCHEMAS } from "./schemaCache";
import type { NodeType } from "./types";

export interface ValidationError {
  nodeId?: string;
  field?: string;
  message: string;
  severity: "error" | "warning";
}
export interface WorkflowValidation {
  valid: boolean;
  errors: ValidationError[];
}

export function validateWorkflow(dsl: WorkflowDSL): WorkflowValidation {
  const errors: ValidationError[] = [];
  const ids = dsl.nodes.map((n) => n.id);
  const idSet = new Set(ids);
  const validTypes = new Set(Object.keys(FALLBACK_SCHEMAS));

  for (const n of dsl.nodes) {
    if (!validTypes.has(n.type)) errors.push({ nodeId: n.id, message: `Invalid node type: ${n.type}`, severity: "error" });
  }

  const seen = new Set<string>();
  for (const id of ids) {
    if (seen.has(id)) errors.push({ message: `Duplicate node id: ${id}`, severity: "error" });
    seen.add(id);
  }

  for (const n of dsl.nodes) {
    for (const dep of n.depends_on ?? []) {
      if (!idSet.has(dep)) errors.push({ nodeId: n.id, message: `Node '${n.id}' depends on unknown node '${dep}'`, severity: "error" });
    }
  }

  const adj = new Map<string, string[]>();
  for (const n of dsl.nodes) adj.set(n.id, n.depends_on ?? []);
  const WHITE = 0, GRAY = 1, BLACK = 2;
  const color = new Map<string, number>();
  const hasCycle = (u: string): boolean => {
    color.set(u, GRAY);
    for (const v of adj.get(u) ?? []) {
      const c = color.get(v) ?? WHITE;
      if (c === GRAY) return true;
      if (c === WHITE && hasCycle(v)) return true;
    }
    color.set(u, BLACK);
    return false;
  };
  for (const n of dsl.nodes) {
    if ((color.get(n.id) ?? WHITE) === WHITE && hasCycle(n.id)) {
      errors.push({ message: `Dependency cycle detected involving '${n.id}'`, severity: "error" });
      break;
    }
  }

  const entries = dsl.nodes.filter((n) => !n.depends_on || n.depends_on.length === 0);
  if (entries.length !== 1) {
    errors.push({ message: `Expected exactly one entry node, got ${entries.length}`, severity: "error" });
  }

  for (const n of dsl.nodes) {
    const schema = getSchema(n.type as NodeType);
    const cfg = (n.config as Record<string, unknown>) ?? {};
    const cfgResult = checkConfig(n.type as NodeType, cfg, schema.validation_rules);
    for (const e of cfgResult.errors) errors.push({ nodeId: n.id, field: e.field, message: e.message, severity: "error" });
    for (const [field, val] of Object.entries(cfg)) {
      if (typeof val === "string") {
        const rr = checkReferences(val, idSet);
        for (const u of rr.unresolved) errors.push({ nodeId: n.id, field, message: `Unresolved reference: ${u}`, severity: "error" });
      }
    }
  }

  return { valid: errors.filter((e) => e.severity === "error").length === 0, errors };
}
