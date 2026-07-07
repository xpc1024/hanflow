"use client";
import { useCanvasStore } from "@/stores/canvasStore";
import { useWorkflowStore } from "@/stores/workflowStore";
import { useUiStore } from "@/stores/uiStore";
import { en } from "@/lib/i18n/en";
import { Wand2, Palette, Save, Play } from "lucide-react";
import { DryRunStatus } from "./dryrun/DryRunStatus";

export function TopBar() {
  const { alignAll, snapToGridAll } = useCanvasStore();
  const { current, saveCurrent, runDryRun } = useWorkflowStore();
  const { toggleTheme } = useUiStore();
  const dirty = current?.dirty ?? false;
  const valid = current?.validation?.valid ?? true;

  const onSave = async () => { const ok = await saveCurrent(); if (!ok) alert("Cannot save: validation errors"); };
  const onDryRun = () => {
    const sel = useCanvasStore.getState().transient.selectedNodeIds[0];
    if (sel) runDryRun({ nodeId: sel, inputs: {} });
    else runDryRun({ inputs: {} });
  };

  return (
    <>
      <div style={{ height: 48, display: "flex", alignItems: "center", gap: 8, padding: "0 16px", borderBottom: "1px solid var(--panel-border)", background: "var(--panel-bg)" }}>
        <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>{current?.dsl.name ?? "Untitled"}</span>
        {dirty && <span style={{ color: "var(--accent)", fontSize: 20 }}>*</span>}
        <div style={{ flex: 1 }} />
        <button onClick={onSave} disabled={!dirty} style={dirty ? activeBtn : inactiveBtn}><Save size={14} /> Save</button>
        <span style={{ color: valid ? "var(--status-success)" : "var(--danger)", fontSize: 12 }}>
          {valid ? `${current?.dsl.nodes.length ?? 0} valid` : `${current?.validation.errors.length ?? 0} errors`}
        </span>
        <button onClick={onDryRun} style={toolBtn}><Wand2 size={14} /> Dry-run</button>
        <button disabled title="Available in Monitor (Phase 15)" style={inactiveBtn}><Play size={14} /> Run</button>
        <button onClick={() => alignAll()} style={toolBtn}>{en.topbar.autoAlign}</button>
        <button onClick={() => toggleTheme()} style={toolBtn}><Palette size={14} /></button>
      </div>
      <div style={{ height: 28, display: "flex", alignItems: "center", gap: 16, padding: "0 16px", borderBottom: "1px solid var(--panel-border)", background: "var(--panel-bg)" }}>
        <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>{useCanvasStore.getState().nodes.length} nodes</span>
        <DryRunStatus />
      </div>
    </>
  );
}

const toolBtn: React.CSSProperties = { display: "flex", gap: 4, alignItems: "center", padding: "6px 12px", borderRadius: 6, border: "1px solid var(--node-border)", background: "transparent", color: "var(--text-primary)", cursor: "pointer", fontSize: 12 };
const activeBtn: React.CSSProperties = { ...toolBtn, background: "var(--accent)", color: "#fff", border: "none" };
const inactiveBtn: React.CSSProperties = { ...toolBtn, opacity: 0.5, cursor: "not-allowed" };
