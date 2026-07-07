"use client";
import { useCanvasStore } from "@/stores/canvasStore";
import { useUiStore } from "@/stores/uiStore";
import { en } from "@/lib/i18n/en";
import { Wand2, Palette } from "lucide-react";

export function TopBar() {
  const { alignAll, snapToGridAll } = useCanvasStore();
  const { toggleTheme } = useUiStore();

  return (
    <div
      style={{
        height: 48,
        display: "flex",
        alignItems: "center",
        gap: 8,
        padding: "0 16px",
        borderBottom: "1px solid var(--panel-border)",
        background: "var(--panel-bg)",
      }}
    >
      <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>Hanflow Studio</span>
      <div style={{ flex: 1 }} />
      <button onClick={() => alignAll()} style={btnStyle}>
        <Wand2 size={14} /> {en.topbar.autoAlign}
      </button>
      <button onClick={() => snapToGridAll()} style={btnStyle}>
        {en.topbar.snapToGrid}
      </button>
      <button onClick={() => toggleTheme()} style={btnStyle}>
        <Palette size={14} /> {en.topbar.theme}
      </button>
    </div>
  );
}

const btnStyle: React.CSSProperties = {
  display: "flex",
  gap: 4,
  alignItems: "center",
  padding: "6px 12px",
  borderRadius: 6,
  border: "1px solid var(--node-border)",
  background: "transparent",
  color: "var(--text-primary)",
  cursor: "pointer",
  fontSize: 12,
};
