"use client";
interface Props { name: string; value: number; onChange: (v: number) => void; schema?: { minimum?: number; maximum?: number }; error?: string; }
export function NumberField({ name, value, onChange, schema, error }: Props) {
  return (
    <div style={{ marginBottom: 12 }}>
      <label style={{ display: "block", fontSize: 13, color: "var(--text-secondary)", marginBottom: 4 }}>{name}</label>
      <input type="number" value={value} min={schema?.minimum} max={schema?.maximum}
        onChange={(e) => onChange(Number(e.target.value))} style={inputStyle} />
      {error && <div style={{ color: "var(--danger)", fontSize: 12, marginTop: 4 }}>{error}</div>}
    </div>
  );
}
const inputStyle: React.CSSProperties = {
  width: "100%", background: "var(--node-bg)", border: "1px solid var(--node-border)",
  borderRadius: 6, color: "var(--text-primary)", padding: "8px 12px", fontSize: 13, outline: "none",
};
