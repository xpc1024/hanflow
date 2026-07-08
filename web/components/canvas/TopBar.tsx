"use client";
import { useRouter } from "next/navigation";
import { useCanvasStore } from "@/stores/canvasStore";
import { useWorkflowStore } from "@/stores/workflowStore";
import { useUiStore } from "@/stores/uiStore";
import { en } from "@/lib/i18n/en";
import { Wand2, Palette, Save, Play } from "lucide-react";
import { DryRunStatus } from "./dryrun/DryRunStatus";

export function TopBar() {
  const router = useRouter();
  const { alignAll, snapToGridAll } = useCanvasStore();
  const { current, saveCurrent, runDryRun } = useWorkflowStore();
  const { toggleTheme } = useUiStore();
  const dirty = current?.dirty ?? false;
  const valid = current?.validation?.valid ?? true;
  const nodeCount = useCanvasStore((s) => s.nodes.length);

  // Re-evaluate validation live based on canvas state
  const liveValidation = current?.validation ?? { valid: nodeCount > 0, errors: [] };

  const onSave = async () => {
    if (!current) {
      // No workflow session - create one
      const name = prompt("Workflow name?", "my-flow");
      if (!name) return;
      try {
        await useWorkflowStore.getState().createWorkflow(name);
      } catch (e: any) { alert(e.message); return; }
    }
    const ok = await saveCurrent();
    if (!ok) alert("Cannot save: validation errors. Make sure you have exactly one entry node.");
  };

  const onDryRun = () => {
    if (!current) {
      // Create temp session for dry-run
      useWorkflowStore.getState().setCurrent({
        id: "temp-dryrun",
        dsl: { name: "temp", nodes: [] },
        dirty: false,
        lastSavedAt: null,
        validation: { valid: true, errors: [] },
      });
    }
    const sel = useCanvasStore.getState().transient.selectedNodeIds[0];
    if (sel) runDryRun({ nodeId: sel, inputs: {} });
    else runDryRun({ inputs: {} });
  };

  const onRun = async () => {
    // Save first if dirty
    if (current?.dirty) {
      const ok = await saveCurrent();
      if (!ok) { alert("Cannot run: fix validation errors first"); return; }
    }
    if (!useWorkflowStore.getState().current) {
      alert("Save the workflow first"); return;
    }
    const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    const dsl = useCanvasStore.getState().getDsl(current?.dsl.name ?? "untitled");
    const { toYaml } = await import("@/lib/dsl/yaml");
    const yamlText = toYaml(dsl);
    const r = await fetch(`${API}/api/runs`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ yaml: yamlText, inputs: {} }),
    });
    if (!r.ok) { alert("Failed to start run"); return; }
    const { run_id } = await r.json();
    router.push(`/runs/${run_id}`);
  };

  return (
    <>
      <div style={{ height: 48, display: "flex", alignItems: "center", gap: 8, padding: "0 16px", borderBottom: "1px solid var(--panel-border)", background: "var(--panel-bg)" }}>
        <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>{current?.dsl.name ?? "Untitled"}</span>
        {dirty && <span style={{ color: "var(--accent)", fontSize: 20 }}>*</span>}
        <div style={{ flex: 1 }} />
        <button onClick={onSave} disabled={!dirty} style={dirty ? activeBtn : inactiveBtn}><Save size={14} /> Save</button>
        <span style={{ color: liveValidation.valid && nodeCount > 0 ? "var(--status-success)" : "var(--danger)", fontSize: 12 }}>
          {nodeCount > 0 ? `${nodeCount} nodes` : "empty"} {!liveValidation.valid ? `(${liveValidation.errors.length} errors)` : ""}
        </span>
        <button onClick={onDryRun} style={toolBtn}><Wand2 size={14} /> Dry-run</button>
        <button onClick={onRun} style={nodeCount > 0 ? activeBtn : inactiveBtn} disabled={nodeCount === 0}><Play size={14} /> Run</button>
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
