"use client";
import { formatDryRunOutput } from "@/lib/dsl/dryRun";

export function NodeOutputBadge({ nodeType, output, error }: { nodeType: string; output?: any; error?: string }) {
  if (error) return <div style={{ padding: "4px 12px", fontSize: 11, color: "var(--danger)", fontFamily: "var(--font-mono)" }}>{`> error: ${error.slice(0, 30)}`}</div>;
  if (!output) return null;
  const { summary } = formatDryRunOutput(nodeType, output);
  return <div style={{ padding: "4px 12px", fontSize: 11, color: "var(--text-secondary)", fontFamily: "var(--font-mono)", background: "var(--canvas-bg-grid)", borderRadius: 4, margin: "0 8px 4px" }}>{`> ${summary}`}</div>;
}
