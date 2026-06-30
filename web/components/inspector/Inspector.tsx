"use client";

import { useMemo } from "react";
import { CONFIG_SCHEMA, NODE_META } from "@/lib/dsl/nodeMeta";
import type { CanvasNodeData } from "@/lib/dsl/transform";
import type { Node } from "@xyflow/react";

/**
 * Schema-driven configuration panel for the selected node.
 * Renders a form field per key in CONFIG_SCHEMA[nodeType]; the field type
 * (string/integer/boolean/array/object) decides the input widget. On change,
 * calls onDataChange to update the node's config (caller persists to DSL).
 */
export function Inspector({
  node,
  onDataChange,
}: {
  node: Node<CanvasNodeData> | null;
  onDataChange: (nodeId: string, config: Record<string, unknown>) => void;
}) {
  const schema = useMemo(() => {
    if (!node) return null;
    return CONFIG_SCHEMA[node.data.nodeType] ?? {};
  }, [node]);

  if (!node || !schema) {
    return (
      <aside style={{ width: 300, padding: 16, borderLeft: "1px solid #e5e7eb" }}>
        <p style={{ color: "#9ca3af" }}>Select a node to edit its config.</p>
      </aside>
    );
  }

  const meta = NODE_META[node.data.nodeType];
  const config = node.data.config ?? {};

  return (
    <aside
      style={{
        width: 300,
        padding: 16,
        borderLeft: "1px solid #e5e7eb",
        overflowY: "auto",
      }}
    >
      <h3 style={{ margin: "0 0 4px", color: meta?.color }}>
        {meta?.icon} {meta?.label}
      </h3>
      <p style={{ margin: "0 0 16px", fontSize: 12, color: "#6b7280" }}>{node.data.label}</p>

      {Object.entries(schema).map(([key, typeSpec]) => {
        const required = !typeSpec.endsWith("?");
        const fieldType = typeSpec.replace("?", "");
        const value = config[key];

        return (
          <div key={key} style={{ marginBottom: 12 }}>
            <label style={{ fontSize: 12, fontWeight: 600, display: "block", marginBottom: 4 }}>
              {key}
              {!required && <span style={{ color: "#9ca3af", fontWeight: 400 }}> (optional)</span>}
            </label>
            {renderField(fieldType, value, (v) =>
              onDataChange(node.id, { ...config, [key]: v })
            )}
          </div>
        );
      })}
    </aside>
  );
}

function renderField(
  type: string,
  value: unknown,
  onChange: (v: unknown) => void
) {
  switch (type) {
    case "string":
      return (
        <input
          type="text"
          value={(value as string) ?? ""}
          onChange={(e) => onChange(e.target.value)}
          style={inputStyle}
        />
      );
    case "integer":
      return (
        <input
          type="number"
          value={(value as number) ?? ""}
          onChange={(e) => onChange(Number(e.target.value))}
          style={inputStyle}
        />
      );
    case "boolean":
      return (
        <input
          type="checkbox"
          checked={Boolean(value)}
          onChange={(e) => onChange(e.target.checked)}
        />
      );
    case "array":
      return (
        <textarea
          value={Array.isArray(value) ? (value as string[]).join(", ") : ""}
          onChange={(e) =>
            onChange(e.target.value.split(",").map((s) => s.trim()).filter(Boolean))
          }
          style={{ ...inputStyle, minHeight: 40 }}
          placeholder="comma-separated"
        />
      );
    case "object":
    case "any":
      return (
        <textarea
          value={typeof value === "string" ? value : JSON.stringify(value ?? {}, null, 2)}
          onChange={(e) => {
            try {
              onChange(JSON.parse(e.target.value));
            } catch {
              onChange(e.target.value); // keep raw string while editing
            }
          }}
          style={{ ...inputStyle, minHeight: 60, fontFamily: "monospace", fontSize: 11 }}
        />
      );
    default:
      return <input type="text" value={String(value ?? "")} onChange={(e) => onChange(e.target.value)} style={inputStyle} />;
  }
}

const inputStyle: React.CSSProperties = {
  width: "100%",
  padding: "6px 8px",
  border: "1px solid #d1d5db",
  borderRadius: 4,
  fontSize: 13,
};
