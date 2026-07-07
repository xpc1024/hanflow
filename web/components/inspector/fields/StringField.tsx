"use client";
interface Props { name: string; value: string; onChange: (v: string) => void; schema?: any; error?: string; }
export function StringField({ name, value, onChange, schema, error }: Props) {
  const isTextarea = schema?.format === "textarea";
  return (
    <div style={{ marginBottom: 12 }}>
      <label style={{ display: "block", fontSize: 13, color: "var(--text-secondary)", marginBottom: 4 }}>{name}</label>
      {isTextarea ? (
        <textarea value={value} onChange={(e) => onChange(e.target.value)} rows={4} style={inputStyle} />
      ) : (
        <input type="text" value={value} onChange={(e) => onChange(e.target.value)} style={inputStyle} />
      )}
      {error && <div style={{ color: "var(--danger)", fontSize: 12, marginTop: 4 }}>{error}</div>}
    </div>
  );
}
const inputStyle: React.CSSProperties = {
  width: "100%", background: "var(--node-bg)", border: "1px solid var(--node-border)",
  borderRadius: 6, color: "var(--text-primary)", padding: "8px 12px", fontSize: 13, outline: "none",
};
