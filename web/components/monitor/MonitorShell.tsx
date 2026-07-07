"use client";
import { useEffect } from "react";
import { useMonitorStore } from "@/stores/monitorStore";
import { useRunStream } from "@/hooks/useRunStream";
import { WorkflowCanvas } from "@/components/canvas/WorkflowCanvas";
import { useCanvasStore } from "@/stores/canvasStore";
import { useWorkflowStore } from "@/stores/workflowStore";
import { useRouter } from "next/navigation";

interface Props { runId: string; }

export function MonitorShell({ runId }: Props) {
  const router = useRouter();
  const { current, loadRuns } = useMonitorStore();
  useRunStream(current?.live ? runId : null);
  const nodeRuns = current?.nodeRuns ?? {};

  useEffect(() => { useMonitorStore.getState().openMonitor(runId); }, [runId]);

  const onCancel = async () => {
    if (!confirm(`Cancel run ${runId}?`)) return;
    await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/runs/${runId}`, { method: "DELETE" });
    useMonitorStore.getState().openMonitor(runId);
  };

  const onEditCopy = async () => {
    const { current: wf } = useWorkflowStore.getState();
    if (!wf) { alert("Workflow not loaded"); return; }
    const newName = `Copy of ${wf.id}`;
    const { stringify } = await import("yaml");
    const yamlText = stringify({ workflow: wf.dsl });
    const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    const r = await fetch(`${API}/api/workflows`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: newName, yaml: yamlText }),
    });
    if (r.ok) router.push(`/workflows/${newName}`);
    else alert("Failed to create copy");
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", background: "var(--canvas-bg)", color: "var(--text-primary)" }}>
      {/* Header */}
      <div style={{ height: 48, display: "flex", alignItems: "center", gap: 12, padding: "0 16px", borderBottom: "1px solid var(--panel-border)", background: "var(--panel-bg)" }}>
        <span style={{ fontWeight: 600 }}>Run {runId.slice(0, 8)} | {current?.status ?? "loading"}</span>
        <div style={{ flex: 1 }} />
        <button onClick={onEditCopy} style={btnStyle}>Edit a copy</button>
        {current?.live && <button onClick={onCancel} style={{ ...btnStyle, borderColor: "var(--danger)", color: "var(--danger)" }}>Cancel</button>}
      </div>
      {/* Body: canvas (readOnly) + side panel */}
      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        <div style={{ flex: 1, position: "relative" }}>
          <WorkflowCanvas readOnly />
        </div>
        {/* Right: events log */}
        <div style={{ width: 320, borderLeft: "1px solid var(--panel-border)", background: "var(--panel-bg)", overflow: "auto", padding: 12 }}>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Events</div>
          {(current?.events ?? []).slice(-50).map((e, i) => (
            <div key={i} style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-secondary)", marginBottom: 2 }}>
              {e.kind} {e.node_id ?? ""}
            </div>
          ))}
          {current && current.reconnect.state !== "connected" && current.reconnect.state !== "off" && (
            <div style={{ fontSize: 11, color: "var(--warning)" }}>Reconnecting... ({current.reconnect.state})</div>
          )}
        </div>
      </div>
    </div>
  );
}

const btnStyle: React.CSSProperties = {
  padding: "6px 12px", borderRadius: 6, border: "1px solid var(--node-border)",
  background: "transparent", color: "var(--text-primary)", cursor: "pointer", fontSize: 12,
};
