"use client";
import { useWorkflowStore } from "@/stores/workflowStore";

export function DryRunStatus() {
  const dr = useWorkflowStore((s) => s.dryRun);
  if (!dr) return null;
  const ok = dr.results.filter((r) => r.status === "ok").length;
  const err = dr.results.filter((r) => r.status === "error").length;
  if (dr.running) return <span style={{ color: "var(--accent)", fontSize: 12 }}>Dry-running... {dr.results.length} nodes</span>;
  return <span style={{ color: err > 0 ? "var(--danger)" : "var(--status-success)", fontSize: 12 }}>Dry-run: Done | {ok} ok{err > 0 ? `, ${err} error(s)` : ""}</span>;
}
