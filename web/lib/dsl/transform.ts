import type { Edge, Node } from "@xyflow/react";
import type { WorkflowDSL, WorkflowNode, NodeType } from "./types";

export interface CanvasNodeData {
  label: string;
  nodeType: NodeType;
  config?: Record<string, unknown>;
  condition?: string | null;
  on_error?: Record<string, unknown>;
  retry?: Record<string, unknown> | null;
  timeout_seconds?: number | null;
  sensitivity?: "public" | "internal" | "confidential" | "restricted";
  disabled?: boolean;
  [key: string]: unknown;
}

export type CanvasNode = Node<CanvasNodeData>;

export interface CanvasNote {
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
  text: string;
  color: "yellow" | "green" | "blue" | "pink";
}

export interface CanvasMeta {
  positions: Record<string, { x: number; y: number }>;
  notes: CanvasNote[];
  edgeStyle?: Record<string, "bezier" | "step">;
  background?: "dots" | "grid";
  collapsed?: Record<string, boolean>;
  layoutDir?: "TB" | "LR";
}

function pickMeta(dsl: WorkflowDSL): CanvasMeta {
  const c = (dsl.metadata?.canvas ?? {}) as Partial<CanvasMeta>;
  return {
    positions: (c.positions ?? {}) as Record<string, { x: number; y: number }>,
    notes: (c.notes ?? []) as CanvasNote[],
    edgeStyle: c.edgeStyle,
    background: c.background,
    collapsed: c.collapsed,
    layoutDir: c.layoutDir,
  };
}

export function dslToCanvas(dsl: WorkflowDSL): {
  nodes: CanvasNode[];
  edges: Edge[];
  meta: CanvasMeta;
} {
  const meta = pickMeta(dsl);

  const nodes: CanvasNode[] = dsl.nodes.map((n) => ({
    id: n.id,
    type: "canvasNode",
    position: meta.positions[n.id] ?? { x: 0, y: 0 },
    data: {
      label: n.id,
      nodeType: n.type,
      config: n.config,
      condition: n.condition,
      on_error: n.on_error,
      retry: n.retry,
      timeout_seconds: n.timeout_seconds,
      sensitivity: n.sensitivity,
      disabled: n.disabled,
    },
  }));

  const edges: Edge[] = [];
  for (const n of dsl.nodes) {
    for (const dep of n.depends_on ?? []) {
      edges.push({ id: `${dep}->${n.id}`, source: dep, target: n.id });
    }
  }

  return { nodes, edges, meta };
}

export function canvasToDsl(
  nodes: CanvasNode[],
  edges: Edge[],
  meta: { name: string; description?: string; version?: string } & Partial<CanvasMeta>
): WorkflowDSL {
  const depsByNode: Record<string, string[]> = {};
  for (const e of edges) {
    (depsByNode[e.target] ??= []).push(e.source);
  }

  const positions: Record<string, { x: number; y: number }> = {};
  const dslNodes: WorkflowNode[] = nodes.map((n) => {
    positions[n.id] = n.position;
    const d = n.data;
    const node: WorkflowNode = {
      id: n.id,
      type: d.nodeType,
      config: d.config,
    };
    if (d.condition !== undefined) node.condition = d.condition ?? undefined;
    if (d.on_error !== undefined) node.on_error = d.on_error;
    if (d.retry !== undefined) node.retry = d.retry;
    if (d.timeout_seconds !== undefined) node.timeout_seconds = d.timeout_seconds;
    if (d.sensitivity !== undefined) node.sensitivity = d.sensitivity;
    if (d.disabled !== undefined) node.disabled = d.disabled;
    const deps = depsByNode[n.id];
    if (deps && deps.length > 0) node.depends_on = deps;
    return node;
  });

  const canvasMeta: Record<string, unknown> = { positions };
  const m = meta as CanvasMeta;
  if (m.notes && m.notes.length > 0) canvasMeta.notes = m.notes;
  if (m.edgeStyle) canvasMeta.edgeStyle = m.edgeStyle;
  if (m.background) canvasMeta.background = m.background;
  if (m.collapsed) canvasMeta.collapsed = m.collapsed;
  if (m.layoutDir) canvasMeta.layoutDir = m.layoutDir;

  return {
    name: meta.name,
    description: meta.description,
    version: meta.version,
    nodes: dslNodes,
    metadata: { canvas: canvasMeta },
  };
}
