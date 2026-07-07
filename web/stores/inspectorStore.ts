import { create } from "zustand";
import type { SensitivityLevel } from "@/lib/dsl/types";

interface DraftNode {
  id?: string;
  condition?: string | null;
  on_error?: Record<string, unknown>;
  retry?: Record<string, unknown> | null;
  timeout_seconds?: number | null;
  sensitivity?: SensitivityLevel;
  disabled?: boolean;
}

interface InspectorState {
  open: boolean;
  nodeId: string | null;
  activeTab: "node" | "config" | "advanced";
  draftConfig: Record<string, unknown> | null;
  originalConfig: Record<string, unknown> | null;
  draftNode: Partial<DraftNode> | null;
  originalNode: Partial<DraftNode> | null;
  draftDirty: boolean;
  openInspector: (nodeId: string, config: Record<string, unknown>, node: Partial<DraftNode>) => void;
  closeInspector: () => void;
  setTab: (tab: "node" | "config" | "advanced") => void;
  updateDraftConfig: (field: string, value: unknown) => void;
  updateDraftNode: (field: keyof DraftNode, value: unknown) => void;
  commitDraft: (onCommit: (nodeId: string, config: Record<string, unknown>, node: Partial<DraftNode>) => void) => void;
  discardDraft: () => void;
}

const deep = <T,>(v: T): T =>
  typeof structuredClone === "function" ? structuredClone(v) : JSON.parse(JSON.stringify(v));

export const useInspectorStore = create<InspectorState>((set, get) => ({
  open: false,
  nodeId: null,
  activeTab: "config",
  draftConfig: null,
  originalConfig: null,
  draftNode: null,
  originalNode: null,
  draftDirty: false,

  openInspector: (nodeId, config, node) =>
    set({
      open: true,
      nodeId,
      draftConfig: deep(config),
      originalConfig: deep(config),
      draftNode: deep(node),
      originalNode: deep(node),
      draftDirty: false,
      activeTab: "config",
    }),

  closeInspector: () =>
    set({
      open: false,
      nodeId: null,
      draftConfig: null,
      originalConfig: null,
      draftNode: null,
      originalNode: null,
      draftDirty: false,
    }),

  setTab: (tab) => set({ activeTab: tab }),

  updateDraftConfig: (field, value) =>
    set((s) => ({
      draftConfig: { ...(s.draftConfig ?? {}), [field]: value },
      draftDirty: true,
    })),

  updateDraftNode: (field, value) =>
    set((s) => ({
      draftNode: { ...(s.draftNode ?? {}), [field]: value },
      draftDirty: true,
    })),

  commitDraft: (onCommit) => {
    const { nodeId, draftConfig, draftNode } = get();
    if (nodeId && draftConfig) onCommit(nodeId, draftConfig, draftNode ?? {});
    set({
      draftDirty: false,
      originalConfig: draftConfig ? deep(draftConfig) : null,
      originalNode: draftNode ? deep(draftNode) : null,
    });
  },

  discardDraft: () =>
    set((s) => ({
      draftConfig: s.originalConfig ? deep(s.originalConfig) : null,
      draftNode: s.originalNode ? deep(s.originalNode) : null,
      draftDirty: false,
    })),
}));
