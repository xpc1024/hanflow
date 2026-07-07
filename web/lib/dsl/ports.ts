import type { Edge } from "@xyflow/react";

export interface ConnectResult {
  ok: boolean;
  reason?: string;
}

export function canConnect(source: string, target: string, edges: Edge[]): ConnectResult {
  if (source === target) return { ok: false, reason: "Cannot connect a node to itself" };
  if (edges.some((e) => e.source === source && e.target === target))
    return { ok: false, reason: "Connection already exists" };

  // Cycle detection: DFS on adjacency including candidate edge
  const adj = new Map<string, string[]>();
  const addToAdj = (s: string, t: string) => {
    const arr = adj.get(s);
    if (arr) arr.push(t);
    else adj.set(s, [t]);
  };
  for (const e of edges) addToAdj(e.source, e.target);
  addToAdj(source, target);

  const WHITE = 0,
    GRAY = 1,
    BLACK = 2;
  const color = new Map<string, number>();
  const hasCycle = (u: string): boolean => {
    color.set(u, GRAY);
    for (const v of adj.get(u) ?? []) {
      const c = color.get(v) ?? WHITE;
      if (c === GRAY) return true;
      if (c === WHITE && hasCycle(v)) return true;
    }
    color.set(u, BLACK);
    return false;
  };
  for (const k of Array.from(adj.keys())) {
    if ((color.get(k) ?? WHITE) === WHITE && hasCycle(k)) {
      return { ok: false, reason: "Would create a cycle" };
    }
  }
  return { ok: true };
}
