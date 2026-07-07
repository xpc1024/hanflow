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

interface Props {
  sourceId: string;
  onClose: () => void;
}

export function PlusButtonMenu({ sourceId, onClose }: Props) {
  const [q, setQ] = useState("");
  const { addNodeContinuation } = useCanvasStore();
  const filtered = ALL_TYPES.filter((t) => t.toLowerCase().includes(q.toLowerCase()));

  const pick = (t: NodeType) => {
    const id = `${t.toLowerCase()}_${Date.now().toString(36).slice(-4)}`;
    addNodeContinuation(sourceId, { id, type: t });
    onClose();
  };

  return (
    <div
      style={{
        position: "absolute",
        zIndex: 50,
        background: "var(--panel-bg)",
        border: "1px solid var(--panel-border)",
        borderRadius: 8,
        padding: 8,
        width: 200,
      }}
    >
      <div style={{ display: "flex", gap: 6, alignItems: "center", marginBottom: 8 }}>
        <Search size={14} />
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder={en.palette.search}
          style={{
            background: "transparent",
            border: "none",
            color: "var(--text-primary)",
            outline: "none",
            flex: 1,
            fontSize: 13,
          }}
        />
      </div>
      {GROUP_ORDER.map((g) => {
        const items = filtered.filter((t) => FALLBACK_NODE_META[t].group === g);
        if (items.length === 0) return null;
        return (
          <div key={g}>
            <div style={{ fontSize: 10, color: "var(--text-secondary)", padding: "4px 0" }}>
              {GROUP_LABEL[g]}
            </div>
            {items.map((t) => (
              <button
                key={t}
                onClick={() => pick(t)}
                style={{
                  display: "flex",
                  gap: 8,
                  alignItems: "center",
                  width: "100%",
                  padding: "4px 8px",
                  background: "transparent",
                  border: "none",
                  color: "var(--text-primary)",
                  cursor: "pointer",
                  fontSize: 13,
                }}
              >
                <div
                  style={{
                    width: 4,
                    height: 16,
                    background: FALLBACK_NODE_META[t].color,
                    borderRadius: 2,
                  }}
                />
                {t}
              </button>
            ))}
          </div>
        );
      })}
    </div>
  );
}
