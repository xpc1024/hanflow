"use client";
import { memo, useState } from "react";
import { Handle, Position } from "@xyflow/react";
import { Plus, Copy, Trash2 } from "lucide-react";
import { PlusButtonMenu } from "./PlusButtonMenu";
import { FALLBACK_NODE_META } from "@/lib/dsl/nodeMeta";
import { useCanvasStore } from "@/stores/canvasStore";
import { en } from "@/lib/i18n/en";
import type { CanvasNodeData } from "@/lib/dsl/transform";

interface Props {
  id: string;
  data: CanvasNodeData;
  selected: boolean;
}

export const CanvasNode = memo(function CanvasNode({ id, data, selected }: Props) {
  const [hovered, setHovered] = useState(false);
  const [plusOpen, setPlusOpen] = useState(false);
  const { removeNode, selectNodes } = useCanvasStore();

  const nodeMeta = FALLBACK_NODE_META[data.nodeType];
  const color = nodeMeta?.color ?? "#6b7280";
  const disabled = data.disabled;

  return (
    <div
      data-testid={`canvas-node-${id}`}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => {
        setHovered(false);
        setPlusOpen(false);
      }}
      onClick={(e) => {
        e.stopPropagation();
        selectNodes([id]);
      }}
      style={{
        width: 180,
        borderRadius: 8,
        background: "var(--node-bg)",
        border: `2px solid ${selected ? color : "var(--node-border)"}`,
        boxShadow: selected ? `0 0 0 3px ${color}4D` : "var(--node-shadow)",
        opacity: disabled ? 0.6 : 1,
        filter: disabled ? "grayscale(60%)" : "none",
        position: "relative",
        cursor: "pointer",
      }}
    >
      <Handle type="target" position={Position.Left} data-testid="handle-target" />
      {/* Type color bar */}
      <div style={{ height: 4, background: color, borderRadius: "8px 8px 0 0" }} />
      {/* Title row */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "8px 12px",
        }}
      >
        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
          <span style={{ fontSize: 11, color, fontWeight: 600 }}>{data.nodeType}</span>
          {disabled && (
            <span style={{ fontSize: 10, color: "var(--text-disabled)" }}>
              {en.node.disabled}
            </span>
          )}
        </div>
        {/* Hover actions */}
        {hovered && !disabled && (
          <div style={{ display: "flex", gap: 4 }}>
            <button
              aria-label="Add next node"
              onClick={(e) => {
                e.stopPropagation();
                setPlusOpen(true);
              }}
              style={btnStyle}
            >
              <Plus size={14} />
            </button>
            <button
              aria-label="Copy node"
              onClick={(e) => {
                e.stopPropagation();
                selectNodes([id]);
                useCanvasStore.getState().copySelection();
              }}
              style={btnStyle}
            >
              <Copy size={14} />
            </button>
            <button
              aria-label="Delete node"
              onClick={(e) => {
                e.stopPropagation();
                removeNode(id);
              }}
              style={btnStyle}
            >
              <Trash2 size={14} />
            </button>
          </div>
        )}
      </div>
      {/* Node ID */}
      <div
        style={{
          padding: "0 12px 8px",
          fontSize: 13,
          color: "var(--text-primary)",
        }}
      >
        {data.label}
      </div>
      <Handle type="source" position={Position.Right} data-testid="handle-source" />
      {plusOpen && <PlusButtonMenu sourceId={id} onClose={() => setPlusOpen(false)} />}
    </div>
  );
});

const btnStyle: React.CSSProperties = {
  background: "transparent",
  border: "none",
  color: "var(--text-secondary)",
  cursor: "pointer",
  padding: 2,
  display: "flex",
  alignItems: "center",
};
