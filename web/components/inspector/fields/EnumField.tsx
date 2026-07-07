"use client";
interface Props { name: string; value: string; onChange: (v: string) => void; schema: { enum: string[] }; }
export function EnumField({ name, value, onChange, schema }: Props) {
  return (
    <div style={{ marginBottom: 12 }}>
      <label style={{ display: "block", fontSize: 13, color: "var(--text-secondary)", marginBottom: 4 }}>{name}</label>
      <select value={value} onChange={(e) => onChange(e.target.value)} style={inputStyle}>
        {schema.enum.map((o) => <option key={o} value={o}>{o}</option>)}
      </select>
    </div>
  );
}
const inputStyle: React.CSSProperties = {
  width: "100%", background: "var(--node-bg)", border: "1px solid var(--node-border)",
  borderRadius: 6, color: "var(--text-primary)", padding: "8px 12px", fontSize: 13, outline: "none",
};
