"use client";
import { en } from "@/lib/i18n/en";

export function EmptyState() {
  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        pointerEvents: "none",
        zIndex: 1,
      }}
    >
      <div style={{ fontSize: 32, marginBottom: 8 }}>✨</div>
      <div style={{ fontSize: 18, color: "var(--text-primary)", fontWeight: 600, marginBottom: 4 }}>
        {en.empty.title}
      </div>
      <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>{en.empty.hint}</div>
    </div>
  );
}
