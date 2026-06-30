"use client";

import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api/client";

interface PendingItem {
  run_id: string;
  payload: {
    node_id: string;
    title: string;
    description: string;
    actions: string[];
    timeout_seconds: number | null;
  } | null;
}

/** HITL pending panel: lists paused runs, lets the user approve/reject/reroute. */
export function HitlPanel() {
  const [pending, setPending] = useState<PendingItem[]>([]);
  const [busy, setBusy] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const list = await api.listPendingHitl();
      setPending(list as PendingItem[]);
    } catch {
      // backend not reachable
    }
  }, []);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 5000); // poll every 5s
    return () => clearInterval(interval);
  }, [refresh]);

  const act = useCallback(
    async (runId: string, action: string) => {
      setBusy(runId);
      try {
        if (action === "approve") {
          await api.approveHitl(runId, "web-user");
        }
        // edit/reject/reroute: would open a form; v1 wires approve only
        await refresh();
      } finally {
        setBusy(null);
      }
    },
    [refresh]
  );

  return (
    <div style={{ padding: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h2 style={{ margin: 0, fontSize: 18 }}>🔶 HITL Pending Approvals</h2>
        <button onClick={refresh} style={btn}>↻ Refresh</button>
      </div>

      {pending.length === 0 && (
        <p style={{ color: "#9ca3af", fontSize: 13 }}>No pending approvals.</p>
      )}

      {pending.map((item) => {
        const p = item.payload;
        if (!p) return null;
        return (
          <div
            key={item.run_id}
            style={{
              border: "1px solid #eab308",
              borderRadius: 8,
              padding: 16,
              marginBottom: 12,
              background: "#fefce8",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
              <strong>{p.title}</strong>
              <code style={{ fontSize: 11, color: "#6b7280" }}>{item.run_id.slice(0, 8)}</code>
            </div>
            {p.description && (
              <p style={{ margin: "0 0 12px", fontSize: 13, color: "#4b5563" }}>{p.description}</p>
            )}
            {p.timeout_seconds && (
              <p style={{ margin: "0 0 8px", fontSize: 11, color: "#9ca3af" }}>
                ⏱ Timeout: {p.timeout_seconds}s
              </p>
            )}
            <div style={{ display: "flex", gap: 8 }}>
              {p.actions.includes("approve") && (
                <button
                  onClick={() => act(item.run_id, "approve")}
                  disabled={busy === item.run_id}
                  style={{ ...btn, borderColor: "#22c55e", color: "#22c55e" }}
                >
                  ✓ Approve
                </button>
              )}
              {p.actions.includes("reject") && (
                <button disabled style={{ ...btn, borderColor: "#ef4444", color: "#ef4444", opacity: 0.5 }}>
                  ✗ Reject
                </button>
              )}
              {p.actions.includes("reroute") && (
                <button disabled style={{ ...btn, opacity: 0.5 }}>
                  ↻ Reroute
                </button>
              )}
              {p.actions.includes("edit") && (
                <button disabled style={{ ...btn, opacity: 0.5 }}>
                  ✎ Edit
                </button>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

const btn: React.CSSProperties = {
  padding: "6px 12px",
  border: "1px solid #d1d5db",
  borderRadius: 6,
  background: "#fff",
  cursor: "pointer",
  fontSize: 12,
};
