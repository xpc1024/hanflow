"use client";
interface Props { name: string; value: boolean; onChange: (v: boolean) => void; }
export function BooleanField({ name, value, onChange }: Props) {
  return (
    <div style={{ marginBottom: 12, display: "flex", alignItems: "center", gap: 8 }}>
      <button role="switch" aria-checked={value} onClick={() => onChange(!value)}
        style={{ width: 40, height: 22, borderRadius: 11, border: "none", background: value ? "var(--accent)" : "var(--node-border)", cursor: "pointer", position: "relative" }}>
        <span style={{ position: "absolute", top: 2, left: value ? 20 : 2, width: 18, height: 18, borderRadius: "50%", background: "#fff", transition: "left 0.15s" }} />
      </button>
      <label style={{ fontSize: 13, color: "var(--text-secondary)" }}>{name}</label>
    </div>
  );
}
