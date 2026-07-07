"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useMonitorStore } from "@/stores/monitorStore";

export function RunListPage() {
  const router = useRouter();
  const { runs, loadRuns } = useMonitorStore();
  const [filter, setFilter] = useState<string>("all");

  useEffect(() => {
    loadRuns();
    const interval = setInterval(loadRuns, 5000);
    return () => clearInterval(interval);
  }, [loadRuns]);

  const filtered = filter === "all" ? runs : runs.filter((r: any) => r.status === filter);
  const statuses = ["all", "pending", "running", "paused", "succeeded", "failed", "cancelled"];

  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: "0 auto" }}>
      <h1 style={{ fontSize: 24, color: "var(--text-primary)" }}>Runs</h1>
      <div style={{ display: "flex", gap: 4, marginBottom: 16, marginTop: 16 }}>
        {statuses.map((s) => (
          <button key={s} onClick={() => setFilter(s)} style={filter === s ? activeChip : chip}>{s}</button>
        ))}
      </div>
      {filtered.length === 0 && <div style={{ color: "var(--text-secondary)", padding: 24 }}>No runs yet.</div>}
      {filtered.map((r: any) => (
        <div key={r.run_id} onClick={() => router.push(`/runs/${r.run_id}`)} style={cardStyle}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div style={{ width: 8, height: 8, borderRadius: "50%", background: statusColor(r.status) }} />
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 13 }}>{r.run_id.slice(0, 8)}</span>
            <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>{r.workflow_name ?? ""}</span>
            <div style={{ flex: 1 }} />
            <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>{r.status}</span>
            {r.trigger_source && <span style={{ fontSize: 11, color: "var(--text-disabled)" }}>{r.trigger_source}</span>}
          </div>
        </div>
      ))}
    </div>
  );
}

function statusColor(s: string): string {
  return { running: "#3b82f6", succeeded: "#22c55e", failed: "#ef4444", paused: "#eab308", cancelled: "#6b7280", pending: "#64748b" }[s] ?? "#6b7280";
}

const chip: React.CSSProperties = { padding: "4px 12px", borderRadius: 999, border: "1px solid var(--node-border)", background: "transparent", color: "var(--text-secondary)", cursor: "pointer", fontSize: 12 };
const activeChip: React.CSSProperties = { ...chip, background: "var(--accent)", color: "#fff", border: "none" };
const cardStyle: React.CSSProperties = { padding: "8px 12px", borderRadius: 8, background: "var(--panel-bg)", border: "1px solid var(--node-border)", marginBottom: 8, cursor: "pointer" };
