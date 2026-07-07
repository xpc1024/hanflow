import { create } from "zustand";
import type { WorkflowDSL } from "@/lib/dsl/types";
import { validateWorkflow, type WorkflowValidation } from "@/lib/dsl/validateWorkflow";
import { toYaml, fromYaml } from "@/lib/dsl/yaml";

interface WorkflowMeta {
  id: string; name: string; description: string;
  tags: string[]; nodeCount: number; updatedAt: string | null;
}

interface WorkflowSession {
  id: string;
  dsl: WorkflowDSL;
  dirty: boolean;
  lastSavedAt: string | null;
  validation: WorkflowValidation;
}

interface WorkflowState {
  list: WorkflowMeta[];
  listLoading: boolean;
  current: WorkflowSession | null;
  dryRun: { running: boolean; results: any[]; abortController: AbortController | null } | null;

  loadList: () => Promise<void>;
  setCurrent: (s: WorkflowSession) => void;
  markDirty: () => void;
  createWorkflow: (name: string) => Promise<string>;
  openWorkflow: (id: string) => Promise<void>;
  saveCurrent: () => Promise<boolean>;
  deleteWorkflow: (id: string) => Promise<void>;
  runDryRun: (opts: { nodeId?: string; inputs: Record<string, any> }) => Promise<void>;
  importWorkflow: (yamlText: string, filename: string) => Promise<{ conflict?: boolean; id?: string }>;
  exportCurrent: () => void;
}

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const useWorkflowStore = create<WorkflowState>((set, get) => ({
  list: [], listLoading: false, current: null, dryRun: null,

  loadList: async () => {
    set({ listLoading: true });
    try {
      const r = await fetch(`${API}/api/workflows`);
      set({ list: await r.json(), listLoading: false });
    } catch { set({ listLoading: false }); }
  },

  setCurrent: (s) => set({ current: s }),

  markDirty: () => set((s) => ({ current: s.current ? { ...s.current, dirty: true } : null })),

  createWorkflow: async (name) => {
    const dsl: WorkflowDSL = { name, nodes: [{ id: "start", type: "LLM", config: { template: "" } }] };
    const yamlText = toYaml(dsl);
    const r = await fetch(`${API}/api/workflows`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: name, yaml: yamlText }),
    });
    if (r.status === 409) throw new Error("already exists");
    set({ current: { id: name, dsl, dirty: false, lastSavedAt: new Date().toISOString(), validation: { valid: true, errors: [] } } });
    return name;
  },

  openWorkflow: async (id) => {
    const r = await fetch(`${API}/api/workflows/${id}`);
    if (!r.ok) throw new Error("not found");
    const body = await r.json();
    const dsl = fromYaml(body.yaml);
    set({ current: { id, dsl, dirty: false, lastSavedAt: new Date().toISOString(), validation: validateWorkflow(dsl) } });
    const { useCanvasStore } = await import("@/stores/canvasStore");
    useCanvasStore.getState().setDsl(dsl);
  },

  saveCurrent: async () => {
    const { current } = get();
    if (!current) return false;
    const { useCanvasStore } = await import("@/stores/canvasStore");
    const dsl = useCanvasStore.getState().getDsl(current.dsl.name);
    const validation = validateWorkflow(dsl);
    set((s) => ({ current: s.current ? { ...s.current, dsl, validation } : null }));
    if (!validation.valid) return false;
    const yamlText = toYaml(dsl);
    const r = await fetch(`${API}/api/workflows/${current.id}`, {
      method: "PUT", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: current.id, yaml: yamlText }),
    });
    if (!r.ok) {
      const body = await r.json().catch(() => ({}));
      const errMsg = body.errors?.[0]?.message ?? body.error ?? body.detail ?? "Save failed";
      alert(`Save rejected by server: ${errMsg}`);
      return false;
    }
    set((s) => ({ current: s.current ? { ...s.current, dsl, dirty: false, lastSavedAt: new Date().toISOString() } : null }));
    return true;
  },

  deleteWorkflow: async (id) => {
    await fetch(`${API}/api/workflows/${id}`, { method: "DELETE" });
    await get().loadList();
  },

  runDryRun: async ({ nodeId, inputs }) => {
    const { current } = get();
    if (!current) return;
    const prev = get().dryRun;
    if (prev?.abortController) prev.abortController.abort();
    const ac = new AbortController();
    set({ dryRun: { running: true, results: [], abortController: ac } });
    try {
      const { useCanvasStore } = await import("@/stores/canvasStore");
      const dsl = useCanvasStore.getState().getDsl(current.dsl.name);
      const yamlText = toYaml(dsl);
      const r = await fetch(`${API}/api/workflows/${current.id}/dry-run`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ yaml: yamlText, node_id: nodeId, inputs }),
        signal: ac.signal,
      });
      const reader = r.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const data = JSON.parse(line.slice(6));
            if (data.done) { set((s) => ({ dryRun: s.dryRun ? { ...s.dryRun, running: false } : null })); return; }
            set((s) => ({ dryRun: s.dryRun ? { ...s.dryRun, results: [...s.dryRun.results, data] } : null }));
          }
        }
      }
    } catch (e: any) {
      if (e.name !== "AbortError") set((s) => ({ dryRun: s.dryRun ? { ...s.dryRun, running: false } : null }));
    }
    set((s) => ({ dryRun: s.dryRun ? { ...s.dryRun, running: false } : null }));
  },

  importWorkflow: async (yamlText, filename) => {
    const id = filename.replace(/\.ya?ml$/, "");
    const r = await fetch(`${API}/api/workflows`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id, yaml: yamlText }),
    });
    if (r.status === 409) return { conflict: true };
    return { id };
  },

  exportCurrent: () => {
    const { current } = get();
    if (!current) return;
    const yamlText = toYaml(current.dsl);
    const blob = new Blob([yamlText], { type: "text/yaml" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `${current.id}.yaml`; a.click();
    URL.revokeObjectURL(url);
  },
}));
