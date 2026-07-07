"use client";
import { useState } from "react";
import { Search } from "lucide-react";
import type { NodeType } from "@/lib/dsl/types";
import { FALLBACK_NODE_META } from "@/lib/dsl/nodeMeta";
import { useCanvasStore } from "@/stores/canvasStore";
import { en } from "@/lib/i18n/en";

const ALL_TYPES = Object.keys(FALLBACK_NODE_META) as NodeType[];
const GROUP_ORDER = ["control", "leaf", "dynamic", "state", "retrieval"] as const;
const GROUP_LABEL: Record<string, string> = en.palette.groups;

export function NodePalette() {
  const [q, setQ] = useState("");
  const { addNode } = useCanvasStore();
  const filtered = ALL_TYPES.filter((t) => t.toLowerCase().includes(q.toLowerCase()));

  const onDragStart = (e: React.DragEvent, type: NodeType) => {
    e.dataTransfer.setData("application/reactflow", type);
    e.dataTransfer.effectAllowed = "move";
  };

  const onClick = (type: NodeType) => {
    const id = `${type.toLowerCase()}_${Date.now().toString(36).slice(-4)}`;
    addNode({ id, type, position: { x: 250 + Math.random() * 100, y: 100 + Math.random() * 100 } });
  };

  return (
    <div
      style={{
        width: 240,
        borderRight: "1px solid var(--panel-border)",
        background: "var(--panel-bg)",
        overflow: "auto",
        flexShrink: 0,
      }}
    >
      <div style={{ padding: "12px 12px 8px" }}>
        <div style={{ display: "flex", gap: 6, alignItems: "center", marginBottom: 8 }}>
          <Search size={14} />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder={en.palette.search}
            style={{
              background: "transparent",
              border: "1px solid var(--node-border)",
              borderRadius: 6,
              color: "var(--text-primary)",
              outline: "none",
              flex: 1,
              padding: "4px 8px",
              fontSize: 13,
            }}
          />
        </div>
      </div>
      {GROUP_ORDER.map((g) => {
        const items = filtered.filter((t) => FALLBACK_NODE_META[t].group === g);
        if (items.length === 0) return null;
        return (
          <div key={g} style={{ marginBottom: 8 }}>
            <div
              style={{
                fontSize: 10,
                color: "var(--text-secondary)",
                padding: "4px 12px",
                textTransform: "uppercase",
              }}
            >
              {GROUP_LABEL[g]}
            </div>
            {items.map((t) => (
              <div
                key={t}
                draggable
                onDragStart={(e) => onDragStart(e, t)}
                onClick={() => onClick(t)}
                style={{
                  display: "flex",
                  gap: 8,
                  alignItems: "center",
                  padding: "6px 12px",
                  cursor: "grab",
                  color: "var(--text-primary)",
                  fontSize: 13,
                }}
              >
                <div
                  style={{
                    width: 4,
                    height: 20,
                    background: FALLBACK_NODE_META[t].color,
                    borderRadius: 2,
                  }}
                />
                {t}
              </div>
            ))}
          </div>
        );
      })}
    </div>
  );
}
