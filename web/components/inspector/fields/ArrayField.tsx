"use client";
import { Plus, Trash2 } from "lucide-react";
interface Props { name: string; value: any[]; onChange: (v: any[]) => void; items?: { type: string; enum?: string[] }; }
export function ArrayField({ name, value, onChange, items }: Props) {
  const itemType = items?.type ?? "string";
  const add = () => onChange([...(value ?? []), itemType === "number" ? 0 : ""]);
  const remove = (i: number) => onChange(value.filter((_, idx) => idx !== i));
  const update = (i: number, v: any) => onChange(value.map((x, idx) => (idx === i ? v : x)));
  return (
    <div style={{ marginBottom: 12 }}>
      <label style={{ display: "block", fontSize: 13, color: "var(--text-secondary)", marginBottom: 4 }}>{name}</label>
      {(value ?? []).map((item, i) => (
        <div key={i} style={{ display: "flex", gap: 4, marginBottom: 4 }}>
          <input type={itemType === "number" ? "number" : "text"} value={item}
            onChange={(e) => update(i, itemType === "number" ? Number(e.target.value) : e.target.value)}
            style={{ flex: 1, ...inputStyle }} />
          <button onClick={() => remove(i)} style={iconBtn}><Trash2 size={14} /></button>
        </div>
      ))}
      <button onClick={add} style={addBtn}><Plus size={12} /> Add item</button>
    </div>
  );
}
const inputStyle: React.CSSProperties = { background: "var(--node-bg)", border: "1px solid var(--node-border)", borderRadius: 6, color: "var(--text-primary)", padding: "6px 10px", fontSize: 13, outline: "none" };
const iconBtn: React.CSSProperties = { background: "transparent", border: "none", color: "var(--text-secondary)", cursor: "pointer", padding: 4 };
const addBtn: React.CSSProperties = { background: "transparent", border: "1px dashed var(--node-border)", borderRadius: 6, color: "var(--text-secondary)", padding: "4px 12px", cursor: "pointer", fontSize: 12, display: "flex", gap: 4, alignItems: "center" };
