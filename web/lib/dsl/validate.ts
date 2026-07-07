import type { NodeType } from "./types";

export interface ValidationResult {
  valid: boolean;
  errors: { field?: string; message: string }[];
}

export function checkConfig(
  _nt: NodeType,
  config: Record<string, any>,
  rules: Record<string, any>
): ValidationResult {
  const errors: { field?: string; message: string }[] = [];

  for (const f of (rules.required ?? []) as string[]) {
    if (config[f] === undefined || config[f] === null || config[f] === "") {
      errors.push({ field: f, message: `${f} is required` });
    }
  }

  for (const group of (rules.alternatives ?? []) as string[][]) {
    if (!group.some((f) => config[f] !== undefined && config[f] !== null && config[f] !== "")) {
      errors.push({ message: `Provide one of: ${group.join(" or ")}` });
    }
  }

  for (const [f, r] of Object.entries(rules.ranges ?? {})) {
    const { min, max } = r as { min: number; max: number };
    const v = config[f];
    if (v !== undefined && (typeof v !== "number" || v < min || v > max)) {
      errors.push({ field: f, message: `${f} must be ${min}-${max}` });
    }
  }

  for (const f of (rules.non_empty_if_set ?? []) as string[]) {
    if (config[f] !== undefined && Array.isArray(config[f]) && config[f].length === 0) {
      errors.push({ field: f, message: `${f} must be non-empty if provided` });
    }
  }

  return { valid: errors.length === 0, errors };
}

const REF_RE = /\{\{\s*([A-Za-z_][\w-]*)\./g;

export function checkReferences(
  text: string,
  nodeIds: Set<string>
): { valid: boolean; unresolved: string[] } {
  const unresolved: string[] = [];
  let m: RegExpExecArray | null;
  REF_RE.lastIndex = 0;
  while ((m = REF_RE.exec(text)) !== null) {
    const ref = m[1];
    if (!nodeIds.has(ref) && !unresolved.includes(ref)) unresolved.push(ref);
  }
  return { valid: unresolved.length === 0, unresolved };
}
