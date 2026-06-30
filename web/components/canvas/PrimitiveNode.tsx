"use client";

import { memo } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import { NODE_META } from "@/lib/dsl/nodeMeta";
import type { CanvasNodeData } from "@/lib/dsl/transform";

/**
 * A React Flow node component that renders a primitive with its type-specific
 * color, icon, and label. Registered for all 13 nodeTypes in WorkflowCanvas.
 */
function PrimitiveNodeComponent({ data, selected }: NodeProps) {
  const nodeData = data as CanvasNodeData;
  const meta = NODE_META[nodeData.nodeType];
  if (!meta) return null;

  return (
    <div
      style={{
        border: `2px solid ${meta.color}`,
        borderRadius: 8,
        background: selected ? `${meta.color}22` : "#fff",
        padding: "8px 14px",
        minWidth: 120,
        fontSize: 13,
        fontWeight: 500,
      }}
    >
      <Handle type="target" position={Position.Top} style={{ background: meta.color }} />
      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
        {meta.icon && <span>{meta.icon}</span>}
        <span style={{ color: meta.color }}>{meta.label}</span>
      </div>
      <div style={{ color: "#374151", marginTop: 2, fontSize: 11 }}>{nodeData.label}</div>
      <Handle type="source" position={Position.Bottom} style={{ background: meta.color }} />
    </div>
  );
}

export const PrimitiveNode = memo(PrimitiveNodeComponent);
