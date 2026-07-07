"use client";
import { useState, useEffect } from "react";
import { useWorkflowStore } from "@/stores/workflowStore";

export function NodeOutputDrawer({ onClose }: { onClose: () => void }) {
  const results = useWorkflowStore((s) => s.dryRun?.results ?? []);
  const [selected, setSelected] = useState<string | null>(null);
  useEffect(() => { if (!selected && results.length > 0) setSelected(results[0].node_id); }, [results, selected]);
  const detail = results.find((r) => r.node_id === selected);
  return (
    <div style={{ position: "absolute", bottom: 28, left: 0, right: 0, height: 280, background: "var(--panel-bg)", borderTop: "1px solid var(--panel-border)", display: "flex", zIndex: 20 }}>
      <div style={{ width: 200, borderRight: "1px solid var(--panel-border)", overflow: "auto", padding: 8 }}>
        {results.map((r) => (
          <button key={r.node_id} onClick={() => setSelected(r.node_id)} style={{ display: "block", width: "100%", textAlign: "left", padding: "4px 8px", background: selected === r.node_id ? "var(--accent)" : "transparent", color: "var(--text-primary)", border: "none", cursor: "pointer" }}>{r.node_id}</button>
        ))}
      </div>
      <div style={{ flex: 1, overflow: "auto", padding: 16 }}>
        {detail && <pre style={{ color: "var(--text-primary)", fontFamily: "var(--font-mono)", fontSize: 13 }}>{JSON.stringify(detail.output ?? detail.error ?? {}, null, 2)}</pre>}
      </div>
      <button onClick={onClose} style={{ position: "absolute", top: 8, right: 8, background: "transparent", border: "none", color: "var(--text-secondary)", cursor: "pointer", fontSize: 16 }}>X</button>
    </div>
  );
}
