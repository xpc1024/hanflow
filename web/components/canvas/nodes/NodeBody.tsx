"use client";
import type { NodeType } from "@/lib/dsl/types";
import { getNodeSummary } from "@/lib/dsl/nodeSummary";

interface Props { nodeType: NodeType; config: Record<string, any>; }

export function NodeBody({ nodeType, config }: Props) {
  const summary = getNodeSummary(nodeType, config);
  return (
    <div style={{ padding: "0 12px 8px", fontSize: 12, color: "var(--text-secondary)" }}>
      {summary.lines.map((line, i) => (
        <div key={i} style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{line}</div>
      ))}
    </div>
  );
}
