"use client";
const COLOR: Record<string, string> = {
  idle: "transparent", pending: "#64748b", running: "#3b82f6",
  ok: "#22c55e", error: "#ef4444", skipped: "#6b7280",
};

export function NodeStatusIndicator({ status }: { status: string }) {
  if (status === "idle") return null;
  const color = COLOR[status] ?? "#6b7280";
  const pulse = status === "pending" || status === "running";
  return (
    <div
      data-testid="status-dot"
      data-status={status}
      style={{
        width: 8, height: 8, borderRadius: "50%",
        background: color, display: "inline-block",
        animation: pulse ? "pulse 1s infinite" : "none",
      }}
    />
  );
}
