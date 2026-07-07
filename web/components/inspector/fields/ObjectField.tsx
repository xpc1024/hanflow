"use client";
import { Plus, Trash2 } from "lucide-react";
interface Props { name: string; value: Record<string, any>; onChange: (v: Record<string, any>) => void; }
export function ObjectField({ name, value, onChange }: Props) {
  const entries = Object.entries(value ?? {});
  const updateKey = (oldK: string, newK: string) => {
    const v = value[oldK];
    const next = { ...value };
    delete next[oldK];
    next[newK] = v;
    onChange(next);
  };
  const updateVal = (k: string, v: any) => onChange({ ...value, [k]: v });
  const remove = (k: string) => {
    const next = { ...value };
    delete next[k];
    onChange(next);
  };
  const add = () => onChange({ ...value, [`field_${entries.length}`]: "" });
  return (
    <div style={{ marginBottom: 12 }}>
      <label style={{ display: "block", fontSize: 13, color: "var(--text-secondary)", marginBottom: 4 }}>{name}</label>
      {entries.map(([k, v]) => (
        <div key={k} style={{ display: "flex", gap: 4, marginBottom: 4 }}>
          <input value={k} onChange={(e) => updateKey(k, e.target.value)} placeholder="key" style={{ width: "40%", ...inputStyle }} />
          <input value={typeof v === "string" ? v : JSON.stringify(v)} onChange={(e) => updateVal(k, e.target.value)} placeholder="value" style={{ flex: 1, ...inputStyle }} />
          <button onClick={() => remove(k)} style={iconBtn}><Trash2 size={14} /></button>
        </div>
      ))}
      <button onClick={add} style={addBtn}><Plus size={12} /> Add field</button>
    </div>
  );
}
const inputStyle: React.CSSProperties = { background: "var(--node-bg)", border: "1px solid var(--node-border)", borderRadius: 6, color: "var(--text-primary)", padding: "6px 10px", fontSize: 13, outline: "none" };
const iconBtn: React.CSSProperties = { background: "transparent", border: "none", color: "var(--text-secondary)", cursor: "pointer", padding: 4 };
const addBtn: React.CSSProperties = { background: "transparent", border: "1px dashed var(--node-border)", borderRadius: 6, color: "var(--text-secondary)", padding: "4px 12px", cursor: "pointer", fontSize: 12, display: "flex", gap: 4, alignItems: "center" };
