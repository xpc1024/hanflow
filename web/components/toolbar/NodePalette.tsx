"use client";

import { NODE_META } from "@/lib/dsl/nodeMeta";
import type { NodeType } from "@/lib/dsl/types";
import { useCanvasStore } from "@/stores/canvasStore";

const ALL_TYPES: NodeType[] = [
  "LLM", "Tool", "Research", "Execution",
  "HITL",
  "Coordinator",
  "Memory", "Subworkflow", "Knowledge",
  "Sequential", "Parallel", "Loop", "Branch",
];

/** Palette of 13 primitive buttons — click to add a node to the canvas. */
export function NodePalette() {
  const addNode = useCanvasStore((s) => s.addNode);

  return (
    <div
      style={{
        width: 160,
        padding: 12,
        borderRight: "1px solid #e5e7eb",
        overflowY: "auto",
      }}
    >
      <h4 style={{ margin: "0 0 8px", fontSize: 12, color: "#6b7280" }}>ADD NODE</h4>
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {ALL_TYPES.map((t) => {
          const meta = NODE_META[t];
          return (
            <button
              key={t}
              onClick={() => addNode(t)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                padding: "6px 10px",
                border: `1px solid ${meta.color}`,
                borderRadius: 6,
                background: "#fff",
                cursor: "pointer",
                fontSize: 12,
                fontWeight: 500,
                color: meta.color,
              }}
            >
              {meta.icon && <span>{meta.icon}</span>}
              {meta.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
