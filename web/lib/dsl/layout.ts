import dagre from "@dagrejs/dagre";
import type { Edge, Node } from "@xyflow/react";

/**
 * Auto-layout nodes with dagre (top-to-bottom). User-dragged positions are
 * persisted to metadata.canvas (transform.ts) and override this on reload.
 */
export function layoutDagre(
  nodes: Node[],
  edges: Edge[],
  options: { direction?: "TB" | "LR"; nodeWidth?: number; nodeHeight?: number } = {}
): Node[] {
  const { direction = "TB", nodeWidth = 180, nodeHeight = 80 } = options;
  const g = new dagre.graphlib.Graph();
  g.setGraph({ rankdir: direction, nodesep: 50, ranksep: 80 });
  g.setDefaultEdgeLabel(() => ({}));

  for (const n of nodes) {
    g.setNode(n.id, { width: nodeWidth, height: nodeHeight });
  }
  for (const e of edges) {
    g.setEdge(e.source, e.target);
  }
  dagre.layout(g);

  return nodes.map((n) => {
    const pos = g.node(n.id);
    return { ...n, position: { x: pos.x - nodeWidth / 2, y: pos.y - nodeHeight / 2 } };
  });
}
