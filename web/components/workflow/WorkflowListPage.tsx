"use client";
import { useState, useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";
import { useWorkflowStore } from "@/stores/workflowStore";
import { Plus, Upload, Search } from "lucide-react";
import { en } from "@/lib/i18n/en";

export function WorkflowListPage() {
  const router = useRouter();
  const { list, loadList, createWorkflow, importWorkflow } = useWorkflowStore();
  const [q, setQ] = useState("");
  const [tagFilter, setTagFilter] = useState<string | null>(null);

  useEffect(() => { loadList(); }, [loadList]);

  const allTags = useMemo(() => Array.from(new Set(list.flatMap((w) => w.tags))), [list]);
  const filtered = list.filter((w) =>
    (w.name.toLowerCase().includes(q.toLowerCase()) || w.description.toLowerCase().includes(q.toLowerCase())) &&
    (!tagFilter || w.tags.includes(tagFilter))
  );

  const onNew = async () => {
    const name = prompt("Workflow name?");
    if (!name) return;
    try { const id = await createWorkflow(name); router.push(`/workflows/${id}`); }
    catch (e: any) { alert(e.message); }
  };

  const onImport = () => {
    const input = document.createElement("input");
    input.type = "file"; input.accept = ".yaml,.yml";
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;
      const text = await file.text();
      const r = await importWorkflow(text, file.name);
      if (r.conflict) {
        const choice = confirm(`Workflow already exists. Click OK to Overwrite, or Cancel to keep both.`);
        if (choice) {
          const id = file.name.replace(/\.ya?ml$/, "");
          await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/workflows/${id}`, {
            method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ id, yaml: text }),
          });
          await loadList();
        } else {
          const newName = prompt("New workflow name:", `${file.name.replace(/\.ya?ml$/, "")}_copy`);
          if (newName) {
            await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/workflows`, {
              method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ id: newName, yaml: text }),
            });
            await loadList();
          }
        }
      } else { await loadList(); }
    };
    input.click();
  };

  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: "0 auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <h1 style={{ fontSize: 24, color: "var(--text-primary)" }}>Workflows</h1>
        <div style={{ display: "flex", gap: 8 }}>
          <button onClick={onImport} style={importBtn}><Upload size={16} /> Import</button>
          <button onClick={onNew} style={newBtn}><Plus size={16} /> New Workflow</button>
        </div>
      </div>
      <div style={{ display: "flex", gap: 12, marginBottom: 16, alignItems: "center" }}>
        <div style={{ display: "flex", gap: 6, alignItems: "center", flex: 1 }}>
          <Search size={16} />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search by name or description..." style={searchInput} />
        </div>
        <div style={{ display: "flex", gap: 4 }}>
          <button onClick={() => setTagFilter(null)} style={!tagFilter ? activeChip : chip}>All</button>
          {allTags.map((t) => <button key={t} onClick={() => setTagFilter(t)} style={tagFilter === t ? activeChip : chip}>{t}</button>)}
        </div>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 16 }}>
        {filtered.map((w) => (
          <div key={w.id} onClick={() => router.push(`/workflows/${w.id}`)} style={cardStyle}>
            <div style={{ height: 4, background: "#3b82f6", borderRadius: "12px 12px 0 0" }} />
            <div style={{ padding: 16 }}>
              <div style={{ fontSize: 15, fontWeight: 600, color: "var(--text-primary)" }}>{w.name}</div>
              <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 4 }}>{w.nodeCount} nodes</div>
              {w.description && <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 4 }}>{w.description.slice(0, 60)}</div>}
              {w.tags.length > 0 && (
                <div style={{ display: "flex", gap: 4, marginTop: 8 }}>
                  {w.tags.map((t) => <span key={t} style={tagChip}>{t}</span>)}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
      {list.length === 0 && <div style={{ textAlign: "center", padding: 48, color: "var(--text-secondary)" }}>No workflows yet. Create your first one.</div>}
    </div>
  );
}

const importBtn: React.CSSProperties = { padding: "8px 16px", borderRadius: 8, border: "1px solid var(--node-border)", background: "transparent", color: "var(--text-primary)", cursor: "pointer", display: "flex", gap: 6, alignItems: "center", fontSize: 13 };
const newBtn: React.CSSProperties = { ...importBtn, border: "none", background: "var(--accent)", color: "#fff" };
const searchInput: React.CSSProperties = { flex: 1, background: "transparent", border: "1px solid var(--node-border)", borderRadius: 6, color: "var(--text-primary)", padding: "8px 12px" };
const chip: React.CSSProperties = { padding: "4px 12px", borderRadius: 999, border: "1px solid var(--node-border)", background: "transparent", color: "var(--text-secondary)", cursor: "pointer", fontSize: 12 };
const activeChip: React.CSSProperties = { ...chip, background: "var(--accent)", color: "#fff", border: "none" };
const cardStyle: React.CSSProperties = { borderRadius: 12, background: "var(--panel-bg)", border: "1px solid var(--node-border)", cursor: "pointer", transition: "transform 0.15s" };
const tagChip: React.CSSProperties = { padding: "2px 8px", borderRadius: 999, background: "rgba(59,130,246,0.1)", color: "var(--accent)", fontSize: 11 };
