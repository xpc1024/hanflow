import { create } from "zustand";

interface HitlTodo {
  run_id: string; node_id: string; workflow_name: string;
  title: string; description: string;
  form: Record<string, any>; current_value: any;
  actions: string[]; paused_at: string;
  timeout_seconds: number | null; approver: string | null;
}

interface HitlHistoryItem {
  run_id: string; node_id: string; workflow_name: string;
  action: string; decided_by: string; decided_at: string;
  duration_seconds: number; edited_value?: any;
  reroute_target?: string; reason?: string; form?: any;
}

interface HitlState {
  pending: HitlTodo[];
  history: HitlHistoryItem[];
  filter: "all" | "mine" | "unassigned";
  submitting: { run_id: string; action: string } | null;

  loadPending: () => Promise<void>;
  loadHistory: () => Promise<void>;
  setFilter: (f: "all" | "mine" | "unassigned") => void;
  submitApproval: (runId: string, payload: any) => Promise<boolean>;
}

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const useHitlStore = create<HitlState>((set, get) => ({
  pending: [], history: [], filter: "all", submitting: null,

  loadPending: async () => {
    try {
      const r = await fetch(`${API}/api/hitl/pending`);
      set({ pending: await r.json() });
    } catch {}
  },

  loadHistory: async () => {
    try {
      const r = await fetch(`${API}/api/hitl/history?limit=100`);
      set({ history: await r.json() });
    } catch {}
  },

  setFilter: (f) => set({ filter: f }),

  submitApproval: async (runId, payload) => {
    set({ submitting: { run_id: runId, action: payload.action } });
    try {
      const endpoint = payload.action;
      const r = await fetch(`${API}/api/runs/${runId}/${endpoint}`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (r.status === 409) {
        alert("Already decided by someone else");
        await get().loadPending(); await get().loadHistory();
        return false;
      }
      if (!r.ok) { alert("Submit failed"); return false; }
      await get().loadPending(); await get().loadHistory();
      return true;
    } catch { alert("Network error"); return false; }
    finally { set({ submitting: null }); }
  },
}));
