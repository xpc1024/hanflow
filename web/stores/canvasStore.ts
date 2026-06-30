// Zustand store for Build-mode canvas state: nodes, edges, selected node,
// and actions to add/delete/connect nodes + edit config. The store holds the
// React Flow state directly; canvasToDsl converts it back to a WorkflowDSL on
// demand (export / save).

import { create } from "zustand";
import type { Edge, Node, OnConnect, OnNodesChange, OnEdgesChange } from "@xyflow/react";
import { applyNodeChanges, applyEdgeChanges, addEdge } from "@xyflow/react";
import { DEFAULT_CONFIG } from "@/lib/dsl/nodeMeta";
import type { NodeType } from "@/lib/dsl/types";
import type { CanvasNodeData } from "@/lib/dsl/transform";

interface CanvasStore {
  nodes: Node<CanvasNodeData>[];
  edges: Edge[];
  selectedId: string | null;
  setInitial: (nodes: Node<CanvasNodeData>[], edges: Edge[]) => void;
  onNodesChange: OnNodesChange;
  onEdgesChange: OnEdgesChange;
  onConnect: OnConnect;
  addNode: (type: NodeType) => void;
  deleteNode: (id: string) => void;
  selectNode: (id: string | null) => void;
  updateConfig: (nodeId: string, config: Record<string, unknown>) => void;
}

let idCounter = 100;

export const useCanvasStore = create<CanvasStore>((set, get) => ({
  nodes: [],
  edges: [],
  selectedId: null,

  setInitial: (nodes, edges) => set({ nodes, edges, selectedId: null }),

  onNodesChange: (changes) => {
    set({ nodes: applyNodeChanges(changes, get().nodes) as Node<CanvasNodeData>[] });
  },

  onEdgesChange: (changes) => {
    set({ edges: applyEdgeChanges(changes, get().edges) });
  },

  onConnect: (connection) => {
    set({ edges: addEdge(connection, get().edges) });
  },

  addNode: (type) => {
    const id = `${type.toLowerCase()}-${idCounter++}`;
    const newNode: Node<CanvasNodeData> = {
      id,
      type: "primitive",
      position: { x: 250, y: idCounter * 30 },
      data: {
        label: id,
        nodeType: type,
        config: { ...(DEFAULT_CONFIG[type] ?? {}) },
      },
    };
    set({ nodes: [...get().nodes, newNode], selectedId: id });
  },

  deleteNode: (id) => {
    set({
      nodes: get().nodes.filter((n) => n.id !== id),
      edges: get().edges.filter((e) => e.source !== id && e.target !== id),
      selectedId: get().selectedId === id ? null : get().selectedId,
    });
  },

  selectNode: (id) => set({ selectedId: id }),

  updateConfig: (nodeId, config) => {
    set({
      nodes: get().nodes.map((n) =>
        n.id === nodeId ? { ...n, data: { ...n.data, config } } : n
      ),
    });
  },
}));
