import { create } from "zustand";
import type { NodeRunState, RunEvent } from "@/lib/dsl/runEvent";
import { applyRunEvent } from "@/lib/dsl/runEvent";

interface MonitorSession {
  run_id: string;
  status: string;
  live: boolean;
  events: RunEvent[];
  nodeRuns: Record<string, NodeRunState>;
  artifacts: any[];
  reconnect: { state: "connected" | "fast" | "slow" | "off"; attempts: number };
}

interface MonitorState {
  runs: any[];
  current: MonitorSession | null;
  scrubber: { currentTime: number; totalDuration: number; mode: "live" | "replay" } | null;

  loadRuns: () => Promise<void>;
  openMonitor: (runId: string) => Promise<void>;
  applyEvent: (event: RunEvent) => void;
  setReconnect: (state: string, attempts: number) => void;
  setScrubber: (patch: any) => void;
}

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const useMonitorStore = create<MonitorState>((set) => ({
  runs: [],
  current: null,
  scrubber: null,

  loadRuns: async () => {
    try {
      const r = await fetch(`${API}/api/runs`);
      set({ runs: await r.json() });
    } catch { /* keep stale */ }
  },

  openMonitor: async (runId) => {
    const r = await fetch(`${API}/api/runs/${runId}`);
    const info = await r.json();
    const isLive = info.status === "running" || info.status === "paused";
    set({
      current: {
        run_id: runId,
        status: info.status,
        live: isLive,
        events: [],
        nodeRuns: {},
        artifacts: info.result?.artifacts ?? [],
        reconnect: { state: "connected", attempts: 0 },
      },
    });
  },

  applyEvent: (event) =>
    set((s) => {
      if (!s.current) return {};
      const nodeRuns = applyRunEvent(s.current.nodeRuns, event);
      const events = [...s.current.events, event];
      let artifacts = s.current.artifacts;
      if (event.kind === "artifact_created" && event.data.artifact) artifacts = [...artifacts, event.data.artifact];
      return { current: { ...s.current, nodeRuns, events, artifacts } };
    }),

  setReconnect: (state, attempts) =>
    set((s) =>
      s.current ? { current: { ...s.current, reconnect: { state: state as any, attempts } } } : {}
    ),

  setScrubber: (patch) =>
    set((s) => ({ scrubber: s.scrubber ? { ...s.scrubber, ...patch } : null })),
}));
