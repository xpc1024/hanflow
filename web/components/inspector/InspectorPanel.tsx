"use client";
import { useInspectorStore } from "@/stores/inspectorStore";
import { useCanvasStore } from "@/stores/canvasStore";
import { getSchema } from "@/lib/dsl/schemaCache";
import { checkConfig } from "@/lib/dsl/validate";
import { ConfigForm } from "./ConfigForm";
import type { NodeType } from "@/lib/dsl/types";
import { en } from "@/lib/i18n/en";

interface Props { nodeType: NodeType; }

export function InspectorPanel({ nodeType }: Props) {
  const { open, nodeId, activeTab, draftDirty, draftConfig, draftNode, setTab, closeInspector, commitDraft, discardDraft, updateDraftNode } = useInspectorStore();
  const allNodes = useCanvasStore((s) => s.nodes);
  const nodeIds = new Set(allNodes.map((n) => n.id));

  if (!open || !nodeId) return null;

  const schema = getSchema(nodeType);
  const cfgValid = checkConfig(nodeType, draftConfig ?? {}, schema.validation_rules).valid;
  const applyDisabled = !cfgValid;

  const onChangeTab = (tab: "node" | "config" | "advanced") => {
    if (draftDirty && !applyDisabled) {
      commitDraft((id, c, n) => useCanvasStore.getState().setNodeData(id, { config: c, ...n }));
    }
    setTab(tab);
  };

  const selectedNode = allNodes.find((n) => n.id === nodeId);
  const color = schema.visual.color;

  return (
    <div
      data-testid="inspector"
      style={{
        width: 360, height: "100%", background: "var(--panel-bg)",
        borderLeft: "1px solid var(--panel-border)", display: "flex", flexDirection: "column",
      }}
    >
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 12px", borderBottom: "1px solid var(--panel-border)" }}>
        <div style={{ width: 4, height: 20, background: color, borderRadius: 2 }} />
        <span style={{ fontSize: 13, fontWeight: 600, color }}>{nodeType}</span>
        <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>· {nodeId}</span>
        {draftDirty && <span style={{ color: "var(--accent)", fontSize: 20 }}>•</span>}
        <div style={{ flex: 1 }} />
        <button onClick={closeInspector} style={closeBtn}>✕</button>
      </div>
      {/* Tabs */}
      <div style={{ display: "flex", borderBottom: "1px solid var(--panel-border)" }}>
        {(["node", "config", "advanced"] as const).map((t) => (
          <button key={t} onClick={() => onChangeTab(t)} style={activeTab === t ? activeTabStyle : tabStyle}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>
      {/* Content */}
      <div style={{ flex: 1, overflow: "auto", padding: 16 }}>
        {activeTab === "config" && <ConfigForm nodeType={nodeType} nodeId={nodeId} nodeIds={nodeIds} />}
        {activeTab === "node" && (
          <div>
            <div style={{ marginBottom: 12 }}>
              <label style={labelStyle}>ID</label>
              <input value={draftNode?.id ?? nodeId} onChange={(e) => updateDraftNode("id", e.target.value)} style={inputStyle} />
            </div>
            <div style={{ marginBottom: 12 }}>
              <label style={labelStyle}>Type (read-only)</label>
              <input value={nodeType} disabled style={{ ...inputStyle, opacity: 0.5 }} />
            </div>
          </div>
        )}
        {activeTab === "advanced" && (
          <div>
            <div style={{ marginBottom: 12 }}>
              <label style={labelStyle}>Sensitivity</label>
              <select value={draftNode?.sensitivity ?? "public"} onChange={(e) => updateDraftNode("sensitivity", e.target.value as any)} style={inputStyle}>
                <option value="public">public</option>
                <option value="internal">internal</option>
                <option value="confidential">confidential</option>
                <option value="restricted">restricted</option>
              </select>
            </div>
            <div style={{ marginBottom: 12 }}>
              <label style={labelStyle}>Timeout (seconds)</label>
              <input type="number" value={draftNode?.timeout_seconds ?? ""} onChange={(e) => updateDraftNode("timeout_seconds", e.target.value ? Number(e.target.value) : null)} style={inputStyle} />
            </div>
          </div>
        )}
      </div>
      {/* Footer */}
      {draftDirty && (
        <div style={{ padding: 12, borderTop: "1px solid var(--panel-border)", display: "flex", gap: 8, justifyContent: "flex-end" }}>
          <button onClick={discardDraft} style={discardBtnStyle}>Discard</button>
          <button
            disabled={applyDisabled}
            onClick={() => commitDraft((id, c, n) => {
              if (n.id && n.id !== id) useCanvasStore.getState().renameNode(id, n.id);
              useCanvasStore.getState().setNodeData(id, { config: c, sensitivity: n.sensitivity as any, timeout_seconds: n.timeout_seconds });
            })}
            style={applyDisabled ? disabledApplyBtnStyle : applyBtnStyle}
          >
            Apply
          </button>
        </div>
      )}
    </div>
  );
}

const tabStyle: React.CSSProperties = { flex: 1, padding: "8px 12px", border: "none", borderBottom: "2px solid transparent", background: "transparent", color: "var(--text-secondary)", cursor: "pointer", fontSize: 13, textTransform: "capitalize" };
const activeTabStyle: React.CSSProperties = { ...tabStyle, borderBottom: "2px solid var(--accent)", color: "var(--text-primary)" };
const closeBtn: React.CSSProperties = { background: "transparent", border: "none", color: "var(--text-secondary)", cursor: "pointer", fontSize: 16 };
const labelStyle: React.CSSProperties = { display: "block", fontSize: 13, color: "var(--text-secondary)", marginBottom: 4 };
const inputStyle: React.CSSProperties = { width: "100%", background: "var(--node-bg)", border: "1px solid var(--node-border)", borderRadius: 6, color: "var(--text-primary)", padding: "8px 12px", fontSize: 13, outline: "none" };
const discardBtnStyle: React.CSSProperties = { padding: "6px 16px", borderRadius: 6, border: "1px solid var(--node-border)", background: "transparent", color: "var(--text-primary)", cursor: "pointer", fontSize: 13 };
const applyBtnStyle: React.CSSProperties = { padding: "6px 16px", borderRadius: 6, border: "none", background: "var(--accent)", color: "#fff", cursor: "pointer", fontSize: 13 };
const disabledApplyBtnStyle: React.CSSProperties = { ...applyBtnStyle, background: "var(--node-border)", color: "var(--text-disabled)", cursor: "not-allowed" };
