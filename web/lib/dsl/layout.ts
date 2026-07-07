import dagre from "@dagrejs/dagre";
import type { Edge, Node } from "@xyflow/react";

export function layoutDagre(
  nodes: Node[],
  edges: Edge[],
  options: { direction?: "TB" | "LR"; nodeWidth?: number; nodeHeight?: number } = {}
): Node[] {
  const { direction = "LR", nodeWidth = 180, nodeHeight = 72 } = options;
  const g = new dagre.graphlib.Graph();
  g.setGraph({ rankdir: direction, nodesep: 50, ranksep: 80 });
  g.setDefaultEdgeLabel(() => ({}));
  for (const n of nodes) g.setNode(n.id, { width: nodeWidth, height: nodeHeight });
  for (const e of edges) g.setEdge(e.source, e.target);
  dagre.layout(g);
  return nodes.map((n) => {
    const pos = g.node(n.id);
    return { ...n, position: { x: pos.x - nodeWidth / 2, y: pos.y - nodeHeight / 2 } };
  });
}

export function snapToGrid(p: { x: number; y: number }, grid = 8): { x: number; y: number } {
  return { x: Math.round(p.x / grid) * grid, y: Math.round(p.y / grid) * grid };
}
