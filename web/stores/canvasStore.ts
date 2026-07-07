import { create } from "zustand";
import type { Edge } from "@xyflow/react";
import type { CanvasNode, CanvasNodeData, CanvasMeta, CanvasNote } from "@/lib/dsl/transform";
import type { NodeType } from "@/lib/dsl/types";
import { canConnect } from "@/lib/dsl/ports";
import { layoutDagre, snapToGrid } from "@/lib/dsl/layout";
import { remapIds } from "@/lib/dsl/clipboard";
import { History } from "@/lib/dsl/history";
import type { WorkflowDSL } from "@/lib/dsl/types";
import { dslToCanvas, canvasToDsl } from "@/lib/dsl/transform";

interface EditorTransient {
  selectedNodeIds: string[];
  selectedEdgeIds: string[];
  selectedNoteIds: string[];
  hoveredNodeId: string | null;
  clipboard: { nodes: CanvasNode[]; edges: Edge[]; notes: CanvasNote[] } | null;
}

interface CanvasSnapshot {
  nodes: CanvasNode[];
  edges: Edge[];
  meta: CanvasMeta;
}

interface CanvasState {
  nodes: CanvasNode[];
  edges: Edge[];
  meta: CanvasMeta;
  transient: EditorTransient;
  history: History<CanvasSnapshot>;
  dirty: boolean;

  reset: () => void;
  pushHistory: () => void;
  snapshot: () => CanvasSnapshot;

  addNode: (n: { id: string; type: NodeType; position: { x: number; y: number }; data?: Partial<CanvasNodeData> }) => void;
  addNodeContinuation: (source: string, n: { id: string; type: NodeType }) => void;
  removeNode: (id: string) => void;
  renameNode: (oldId: string, newId: string) => void;
  connect: (source: string, target: string) => boolean;
  disconnect: (edgeId: string) => void;
  moveNode: (id: string, position: { x: number; y: number }, commit?: boolean) => void;
  setDisabled: (id: string, disabled: boolean) => void;
  setNodeData: (id: string, data: Partial<CanvasNodeData>) => void;

  addNote: (note: CanvasNote) => void;
  updateNote: (id: string, patch: Partial<CanvasNote>) => void;
  removeNote: (id: string) => void;

  selectNodes: (ids: string[]) => void;
  selectEdges: (ids: string[]) => void;
  copySelection: () => void;
  paste: () => void;

  undo: () => void;
  redo: () => void;
  alignAll: () => void;
  snapToGridAll: () => void;

  getDsl: (name?: string) => WorkflowDSL;
  setDsl: (dsl: WorkflowDSL) => void;
  setMeta: (patch: Partial<CanvasMeta>) => void;
}

const emptyMeta: CanvasMeta = { positions: {}, notes: [] };
const emptyTransient: EditorTransient = {
  selectedNodeIds: [],
  selectedEdgeIds: [],
  selectedNoteIds: [],
  hoveredNodeId: null,
  clipboard: null,
};

export const useCanvasStore = create<CanvasState>((set, get) => ({
  nodes: [],
  edges: [],
  meta: { ...emptyMeta },
  transient: { ...emptyTransient },
  history: new History<CanvasSnapshot>(50),
  dirty: false,

  reset: () =>
    set({
      nodes: [],
      edges: [],
      meta: { ...emptyMeta },
      transient: { ...emptyTransient },
      dirty: false,
      history: new History<CanvasSnapshot>(50),
    }),

  pushHistory: () => {
    get().history.push(get().snapshot());
    set({ dirty: true });
  },

  snapshot: () => ({
    nodes: structuredClone(get().nodes) as CanvasNode[],
    edges: structuredClone(get().edges) as Edge[],
    meta: structuredClone(get().meta) as CanvasMeta,
  }),

  addNode: ({ id, type, position, data }) => {
    get().pushHistory();
    const node: CanvasNode = {
      id,
      type: "canvasNode",
      position,
      data: { label: id, nodeType: type, ...data } as CanvasNodeData,
    };
    set((s) => ({ nodes: [...s.nodes, node] }));
  },

  addNodeContinuation: (source, { id, type }) => {
    const src = get().nodes.find((n) => n.id === source);
    if (!src) return;
    const position = { x: src.position.x + 220, y: src.position.y + 100 };
    get().pushHistory();
    const node: CanvasNode = {
      id,
      type: "canvasNode",
      position,
      data: { label: id, nodeType: type },
    };
    set((s) => ({
      nodes: [...s.nodes, node],
      edges: [...s.edges, { id: `${source}->${id}`, source, target: id }],
    }));
  },

  removeNode: (id) => {
    get().pushHistory();
    set((s) => ({
      nodes: s.nodes.filter((n) => n.id !== id),
      edges: s.edges.filter((e) => e.source !== id && e.target !== id),
    }));
  },

  renameNode: (oldId, newId) => {
    if (get().nodes.some((n) => n.id === newId)) return;
    get().pushHistory();
    set((s) => ({
      nodes: s.nodes.map((n) =>
        n.id === oldId ? { ...n, id: newId, data: { ...n.data, label: newId } } : n
      ),
      edges: s.edges.map((e) => ({
        ...e,
        source: e.source === oldId ? newId : e.source,
        target: e.target === oldId ? newId : e.target,
        id: e.id.replace(oldId, newId),
      })),
    }));
  },

  connect: (source, target) => {
    const r = canConnect(source, target, get().edges);
    if (!r.ok) return false;
    get().pushHistory();
    set((s) => ({ edges: [...s.edges, { id: `${source}->${target}`, source, target }] }));
    return true;
  },

  disconnect: (edgeId) => {
    get().pushHistory();
    set((s) => ({ edges: s.edges.filter((e) => e.id !== edgeId) }));
  },

  moveNode: (id, position, commit = false) => {
    set((s) => ({
      nodes: s.nodes.map((n) => (n.id === id ? { ...n, position } : n)),
    }));
    if (commit) get().pushHistory();
  },

  setDisabled: (id, disabled) => {
    get().pushHistory();
    set((s) => ({
      nodes: s.nodes.map((n) => (n.id === id ? { ...n, data: { ...n.data, disabled } } : n)),
    }));
  },

  setNodeData: (id, data) => {
    set((s) => ({
      nodes: s.nodes.map((n) => (n.id === id ? { ...n, data: { ...n.data, ...data } } : n)),
    }));
  },

  addNote: (note) => {
    get().pushHistory();
    set((s) => ({ meta: { ...s.meta, notes: [...s.meta.notes, note] } }));
  },

  updateNote: (id, patch) => {
    set((s) => ({
      meta: {
        ...s.meta,
        notes: s.meta.notes.map((n) => (n.id === id ? { ...n, ...patch } : n)),
      },
    }));
  },

  removeNote: (id) => {
    get().pushHistory();
    set((s) => ({ meta: { ...s.meta, notes: s.meta.notes.filter((n) => n.id !== id) } }));
  },

  selectNodes: (ids) => set((s) => ({ transient: { ...s.transient, selectedNodeIds: ids } })),
  selectEdges: (ids) => set((s) => ({ transient: { ...s.transient, selectedEdgeIds: ids } })),

  copySelection: () => {
    const { nodes, edges, transient, meta } = get();
    const sel = nodes.filter((n) => transient.selectedNodeIds.includes(n.id));
    const selEdges = edges.filter(
      (e) => transient.selectedNodeIds.includes(e.source) && transient.selectedNodeIds.includes(e.target)
    );
    const selNotes = meta.notes.filter((n) => transient.selectedNoteIds.includes(n.id));
    set((s) => ({
      transient: {
        ...s.transient,
        clipboard: {
          nodes: structuredClone(sel) as CanvasNode[],
          edges: structuredClone(selEdges) as Edge[],
          notes: structuredClone(selNotes) as CanvasNote[],
        },
      },
    }));
  },

  paste: () => {
    const clip = get().transient.clipboard;
    if (!clip) return;
    const existing = new Set(get().nodes.map((n) => n.id));
    const nodeIds = clip.nodes.map((n) => n.id);
    const { mapping } = remapIds(nodeIds, existing);
    get().pushHistory();
    const newNodes = clip.nodes.map((n) => ({
      ...structuredClone(n),
      id: mapping[n.id],
      position: { x: n.position.x + 40, y: n.position.y + 40 },
      data: { ...n.data, label: mapping[n.id] },
    }));
    const newEdges = clip.edges.map((e) => ({
      ...structuredClone(e),
      id: `${mapping[e.source]}->${mapping[e.target]}`,
      source: mapping[e.source],
      target: mapping[e.target],
    }));
    set((s) => ({ nodes: [...s.nodes, ...newNodes], edges: [...s.edges, ...newEdges] }));
  },

  undo: () => {
    const current = get().snapshot();
    const snap = get().history.undoPop();
    if (snap) {
      get().history.pushRedo(current);
      set({ nodes: snap.nodes, edges: snap.edges, meta: snap.meta });
    }
  },

  redo: () => {
    const current = get().snapshot();
    const snap = get().history.redoPop();
    if (snap) {
      get().history.pushUndo(current);
      set({ nodes: snap.nodes, edges: snap.edges, meta: snap.meta });
    }
  },

  alignAll: () => {
    get().pushHistory();
    const laid = layoutDagre(get().nodes, get().edges, {
      direction: get().meta.layoutDir ?? "LR",
    });
    set((s) => ({
      nodes: laid.map((n) => ({
        ...n,
        position: snapToGrid(n.position),
      })) as CanvasNode[],
    }));
  },

  snapToGridAll: () => {
    get().pushHistory();
    set((s) => ({
      nodes: s.nodes.map((n) => ({ ...n, position: snapToGrid(n.position) })),
    }));
  },

  getDsl: (name) => {
    const { nodes, edges, meta } = get();
    return canvasToDsl(nodes, edges, { name: name ?? "untitled", ...meta });
  },

  setDsl: (dsl) => {
    const { nodes, edges, meta } = dslToCanvas(dsl);
    set({
      nodes: nodes as CanvasNode[],
      edges,
      meta,
      dirty: false,
      history: new History<CanvasSnapshot>(50),
    });
  },

  setMeta: (patch) => set((s) => ({ meta: { ...s.meta, ...patch } })),
}));
