"use client";
import { useEffect, useRef } from "react";
import { useMonitorStore } from "@/stores/monitorStore";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const FAST_DELAYS = [1000, 2000, 4000, 8000, 16000, 30000];
const SLOW_DELAY = 60000;

export function useRunStream(runId: string | null) {
  const wsRef = useRef<WebSocket | null>(null);
  const attemptRef = useRef(0);
  const slowTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!runId) return;
    let cancelled = false;

    const connect = () => {
      const wsUrl = API_BASE.replace(/^http/, "ws") + `/api/runs/${runId}/stream`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => { attemptRef.current = 0; useMonitorStore.getState().setReconnect("connected", 0); };

      ws.onmessage = (e) => {
        const event = JSON.parse(e.data);
        if (event.__done__) { ws.close(); return; }
        useMonitorStore.getState().applyEvent(event);
      };

      ws.onclose = () => {
        if (cancelled) return;
        fetch(`${API_BASE}/api/runs/${runId}`)
          .then((r) => r.json())
          .then((info) => {
            if (["succeeded", "failed", "cancelled"].includes(info.status)) {
              useMonitorStore.getState().setReconnect("off", 0);
              return;
            }
            reconnect();
          })
          .catch(() => reconnect());
      };

      ws.onerror = () => { ws.close(); };
    };

    const reconnect = () => {
      if (attemptRef.current < FAST_DELAYS.length) {
        const delay = FAST_DELAYS[attemptRef.current];
        useMonitorStore.getState().setReconnect("fast", attemptRef.current + 1);
        attemptRef.current++;
        setTimeout(() => { if (!cancelled) connect(); }, delay);
      } else {
        useMonitorStore.getState().setReconnect("slow", attemptRef.current);
        slowTimerRef.current = setTimeout(() => { if (!cancelled) connect(); }, SLOW_DELAY);
      }
    };

    connect();

    return () => {
      cancelled = true;
      if (slowTimerRef.current) clearTimeout(slowTimerRef.current);
      wsRef.current?.close();
    };
  }, [runId]);

  const retryNow = () => {
    attemptRef.current = 0;
    wsRef.current?.close();
  };

  return { retryNow };
}
