"use client";

import { useEffect, useState, useCallback } from "react";
import { api, type RunSummary } from "@/lib/api/client";

interface RunEvent {
  kind: string;
  node_id?: string;
  data?: Record<string, unknown>;
  __done__?: boolean;
}

/** Monitor mode: list runs, select one, stream its RunEvents over WS in real time. */
export function MonitorView() {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [events, setEvents] = useState<RunEvent[]>([]);

  const refreshRuns = useCallback(async () => {
    try {
      const list = await api.listRuns();
      setRuns(list);
    } catch {
      // backend not reachable (dev mode without server)
    }
  }, []);

  useEffect(() => {
    refreshRuns();
  }, [refreshRuns]);

  // Subscribe to WS when a run is selected
  useEffect(() => {
    if (!selectedId) return;
    setEvents([]);
    const ws = new WebSocket(api.wsUrl(selectedId));
    ws.onmessage = (msg) => {
      const ev: RunEvent = JSON.parse(msg.data);
      setEvents((prev) => [...prev, ev]);
      if (ev.__done__) ws.close();
    };
    ws.onerror = () => {
      // WS connection failed (backend not running); stop silently
    };
    return () => ws.close();
  }, [selectedId]);

  return (
    <div style={{ display: "flex", height: "100%", minHeight: 400 }}>
      {/* Run list */}
      <div style={{ width: 280, borderRight: "1px solid #e5e7eb", overflowY: "auto" }}>
        <div style={{ padding: 12, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h3 style={{ margin: 0, fontSize: 14 }}>Runs</h3>
          <button onClick={refreshRuns} style={btn}>↻</button>
        </div>
        {runs.length === 0 && (
          <p style={{ padding: 12, fontSize: 12, color: "#9ca3af" }}>No runs yet. Start one via the API.</p>
        )}
        {runs.map((r) => (
          <div
            key={r.run_id}
            onClick={() => setSelectedId(r.run_id)}
            style={{
              padding: "8px 12px",
              cursor: "pointer",
              background: r.run_id === selectedId ? "#eff6ff" : "#fff",
              borderBottom: "1px solid #f3f4f6",
            }}
          >
            <div style={{ fontSize: 11, fontFamily: "monospace", color: "#374151" }}>
              {r.run_id.slice(0, 8)}
            </div>
            <span style={statusBadge(r.status)}>{r.status}</span>
          </div>
        ))}
      </div>

      {/* Event stream */}
      <div style={{ flex: 1, padding: 16, overflowY: "auto" }}>
        <h3 style={{ margin: "0 0 12px", fontSize: 14 }}>Live Events</h3>
        {!selectedId && <p style={{ color: "#9ca3af" }}>Select a run to view its live event stream.</p>}
        {events.map((ev, i) => (
          <div key={i} style={{ marginBottom: 6, fontSize: 12, fontFamily: "monospace" }}>
            <span style={{ color: eventColor(ev.kind), fontWeight: 600 }}>{ev.kind}</span>
            {ev.node_id && <span style={{ color: "#6b7280" }}> · {ev.node_id}</span>}
            {ev.data && Object.keys(ev.data).length > 0 && (
              <span style={{ color: "#9ca3af" }}> {JSON.stringify(ev.data)}</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function statusBadge(status: string): React.CSSProperties {
  const colors: Record<string, string> = {
    running: "#3b82f6",
    succeeded: "#22c55e",
    failed: "#ef4444",
    paused: "#eab308",
    cancelled: "#6b7280",
  };
  return {
    fontSize: 10,
    fontWeight: 600,
    color: "#fff",
    background: colors[status] ?? "#6b7280",
    padding: "2px 6px",
    borderRadius: 4,
  };
}

function eventColor(kind: string): string {
  const map: Record<string, string> = {
    node_end: "#22c55e",
    node_start: "#3b82f6",
    hitl_paused: "#eab308",
    error: "#ef4444",
    artifact_created: "#a855f7",
  };
  return map[kind] ?? "#6b7280";
}

const btn: React.CSSProperties = {
  padding: "4px 8px",
  border: "1px solid #d1d5db",
  borderRadius: 4,
  background: "#fff",
  cursor: "pointer",
  fontSize: 12,
};
