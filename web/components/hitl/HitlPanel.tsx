"use client";
import { useEffect, useState } from "react";
import { useHitlStore } from "@/stores/hitlStore";
import { computeCountdown } from "@/lib/dsl/timeout";

const PHASE_COLOR: Record<string, string> = {
  normal: "var(--status-success)", warning: "var(--warning)",
  urgent: "var(--danger)", expired: "var(--text-disabled)", none: "var(--text-disabled)",
};

export function HitlPanel() {
  const { pending, history, filter, loadPending, loadHistory, setFilter, submitApproval, submitting } = useHitlStore();
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    loadPending(); loadHistory();
    const interval = setInterval(() => { loadPending(); }, 30000);
    return () => clearInterval(interval);
  }, [loadPending, loadHistory]);

  const filtered = pending; // v1: filter not wired (no user system)

  return (
    <div style={{ padding: 24, maxWidth: 900, margin: "0 auto" }}>
      <h1 style={{ fontSize: 24, color: "var(--text-primary)" }}>HITL Approvals</h1>

      {/* Pending */}
      <div style={{ marginTop: 24 }}>
        <div style={{ fontSize: 14, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 12 }}>
          Pending ({filtered.length})
        </div>
        {filtered.length === 0 && <div style={{ color: "var(--text-disabled)", padding: 16 }}>No pending approvals</div>}
        {filtered.map((todo: any) => {
          const payload = todo.payload || todo;
          const cd = computeCountdown(payload.paused_at, payload.timeout_seconds);
          return (
            <div key={todo.run_id} style={cardStyle}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontSize: 14 }}>{payload.title || payload.node_id}</span>
                <span style={{ fontSize: 12, color: "var(--text-disabled)", fontFamily: "var(--font-mono)" }}>{todo.run_id.slice(0, 8)}</span>
                <div style={{ flex: 1 }} />
                <span style={{ fontSize: 11, color: PHASE_COLOR[cd.phase] }}>{cd.label}</span>
              </div>
              {payload.description && <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 4 }}>{payload.description}</div>}
              {payload.actions && (
                <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
                  {payload.actions.map((a: string) => (
                    <button
                      key={a}
                      disabled={submitting?.run_id === todo.run_id}
                      onClick={async () => {
                        const reason = (a === "reject" || a === "reroute") ? prompt("Reason?") || "" : undefined;
                        const target = a === "reroute" ? prompt("Reroute to which node?") || "" : undefined;
                        await submitApproval(todo.run_id, { action: a, decided_by: "anonymous", reason, reroute_target: target, form: {} });
                      }}
                      style={actionBtn(a)}
                    >
                      {a}
                    </button>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* History */}
      <div style={{ marginTop: 32 }}>
        <div style={{ fontSize: 14, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 12 }}>
          History (last 100)
        </div>
        {history.length === 0 && <div style={{ color: "var(--text-disabled)", padding: 16 }}>No approval history yet</div>}
        {history.map((h, i) => (
          <div key={i} style={{ ...cardStyle, opacity: 0.7 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ fontSize: 14 }}>{actionIcon(h.action)} {h.action}</span>
              <span style={{ fontSize: 12, color: "var(--text-disabled)", fontFamily: "var(--font-mono)" }}>{h.run_id?.slice(0, 8)}</span>
              <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>by {h.decided_by}</span>
              <div style={{ flex: 1 }} />
              <span style={{ fontSize: 11, color: "var(--text-disabled)" }}>{h.duration_seconds?.toFixed(1)}s</span>
            </div>
            {h.reason && <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 4 }}>Reason: {h.reason}</div>}
          </div>
        ))}
      </div>
    </div>
  );
}

function actionIcon(a: string): string {
  return { approve: "\u2713", edit: "\u270E", reject: "\u2717", reroute: "\u21AA" }[a] || "\u2022";
}

function actionBtn(a: string): React.CSSProperties {
  const colors: Record<string, string> = { approve: "#22c55e", reject: "#ef4444", edit: "#3b82f6", reroute: "#3b82f6" };
  return {
    padding: "6px 16px", borderRadius: 6, border: "none",
    background: colors[a] || "var(--accent)", color: "#fff", cursor: "pointer",
    fontSize: 13, textTransform: "capitalize", opacity: 1,
  };
}

const cardStyle: React.CSSProperties = {
  padding: "12px 16px", borderRadius: 8, background: "var(--panel-bg)",
  border: "1px solid var(--node-border)", marginBottom: 8,
};
