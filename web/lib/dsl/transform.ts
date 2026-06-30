import type { Edge, Node } from "@xyflow/react";
import type { WorkflowDSL, WorkflowNode } from "./types";

export interface CanvasNodeData {
  label: string;
  nodeType: WorkflowNode["type"];
  config?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface CanvasState {
  nodes: Node<CanvasNodeData>[];
  edges: Edge[];
}

/**
 * Convert a WorkflowDSL into React Flow nodes + edges.
 * depends_on → edges (source = dependency, target = dependent).
 * Node positions come from dsl.metadata.canvas if present.
 */
export function dslToCanvas(dsl: WorkflowDSL): CanvasState {
  const positions = (dsl.metadata?.canvas ?? {}) as Record<string, { x: number; y: number }>;

  const nodes: Node<CanvasNodeData>[] = dsl.nodes.map((n) => ({
    id: n.id,
    type: "default",
    position: positions[n.id] ?? { x: 0, y: 0 },
    data: {
      label: n.id,
      nodeType: n.type,
      config: n.config,
    },
  }));

  const edges: Edge[] = [];
  for (const n of dsl.nodes) {
    for (const dep of n.depends_on ?? []) {
      edges.push({ id: `${dep}->${n.id}`, source: dep, target: n.id });
    }
  }

  return { nodes, edges };
}

/**
 * Convert React Flow nodes + edges back into a WorkflowDSL.
 * edges → depends_on (target depends on source).
 * Node positions are written to metadata.canvas (round-trip preservation).
 *
 * Round-trip contract: canvasToDsl(dslToCanvas(x)).nodes preserves the
 * original nodes (id/type/config/depends_on/condition/sensitivity). Position
 * metadata is an additive canvas concern, not part of the DSL node equality.
 */
export function canvasToDsl(
  nodes: Node<CanvasNodeData>[],
  edges: Edge[],
  meta: { name: string; description?: string; version?: string }
): WorkflowDSL {
  const depsByNode: Record<string, string[]> = {};
  for (const e of edges) {
    (depsByNode[e.target] ??= []).push(e.source);
  }

  const dslNodes: WorkflowNode[] = nodes.map((n) => {
    const node: WorkflowNode = {
      id: n.id,
      type: n.data.nodeType,
      config: n.data.config,
    };
    const deps = depsByNode[n.id];
    if (deps && deps.length > 0) {
      node.depends_on = deps;
    }
    return node;
  });

  return {
    name: meta.name,
    description: meta.description,
    version: meta.version,
    nodes: dslNodes,
  };
}
