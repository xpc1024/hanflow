"use client";
import { useState, useCallback, useEffect, type DragEvent } from "react";
import { NodePalette } from "./NodePalette";
import { TopBar } from "./TopBar";
import { WorkflowCanvas } from "./WorkflowCanvas";
import { EmptyState } from "./EmptyState";
import { ContextMenu } from "./ContextMenu";
import { KeyboardManager } from "./KeyboardManager";
import { StickyNoteLayer } from "./StickyNote";
import { InspectorPanel } from "@/components/inspector/InspectorPanel";
import { DirtyGuard } from "@/components/DirtyGuard";
import { NodeOutputDrawer } from "./dryrun/NodeOutputDrawer";
import { useCanvasStore } from "@/stores/canvasStore";
import { useInspectorStore } from "@/stores/inspectorStore";
import { useUiStore } from "@/stores/uiStore";
import { useWorkflowStore } from "@/stores/workflowStore";
import { en } from "@/lib/i18n/en";
import type { NodeType } from "@/lib/dsl/types";

interface MenuState {
  x: number;
  y: number;
  target: { kind: "canvas" } | { kind: "node"; nodeId: string };
}

export function StudioShell() {
  const nodes = useCanvasStore((s) => s.nodes);
  const theme = useUiStore((s) => s.theme);
  const { addNode } = useCanvasStore();
  const [menu, setMenu] = useState<MenuState | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const selectedNodeIds = useCanvasStore((s) => s.transient.selectedNodeIds);
  const {
    open: inspectorOpen,
    nodeId: inspectorNodeId,
    draftDirty,
    openInspector,
    closeInspector,
    commitDraft,
    discardDraft,
  } = useInspectorStore();

  const { current, dryRun, markDirty } = useWorkflowStore();

  // Link canvas changes to workflowStore dirty
  useEffect(() => {
    const unsub = useCanvasStore.subscribe((s) => {
      if (s.dirty) markDirty();
    });
    return unsub;
  }, [markDirty]);

  // Inspector linkage
  useEffect(() => {
    if (selectedNodeIds.length !== 1) {
      if (inspectorOpen) {
        if (draftDirty) {
          if (confirm(`Save changes to ${inspectorNodeId}?`)) {
            commitDraft((id, c, n) => useCanvasStore.getState().setNodeData(id, { config: c, ...n }));
          } else { discardDraft(); }
        }
        closeInspector();
      }
      return;
    }
    const targetId = selectedNodeIds[0];
    const target = nodes.find((n) => n.id === targetId);
    if (!target) { closeInspector(); return; }
    if (targetId !== inspectorNodeId) {
      if (draftDirty && inspectorNodeId) {
        if (confirm(`Save changes to ${inspectorNodeId}?`)) {
          commitDraft((id, c, n) => useCanvasStore.getState().setNodeData(id, { config: c, ...n }));
        } else { discardDraft(); }
      }
      openInspector(targetId, (target.data.config as Record<string, unknown>) ?? {}, {
        id: target.id, condition: target.data.condition, on_error: target.data.on_error,
        retry: target.data.retry, timeout_seconds: target.data.timeout_seconds,
        sensitivity: target.data.sensitivity, disabled: target.data.disabled,
      });
    }
  }, [selectedNodeIds, nodes, inspectorOpen, inspectorNodeId, draftDirty, openInspector, closeInspector, commitDraft, discardDraft]);

  // Delete linkage
  useEffect(() => {
    if (inspectorOpen && inspectorNodeId && !nodes.some((n) => n.id === inspectorNodeId)) closeInspector();
  }, [nodes, inspectorOpen, inspectorNodeId, closeInspector]);

  // Dry-run error auto-open drawer
  useEffect(() => {
    if (dryRun && !dryRun.running && dryRun.results.some((r) => r.status === "error")) setDrawerOpen(true);
  }, [dryRun]);

  const onDrop = useCallback((e: DragEvent) => {
    e.preventDefault();
    const type = e.dataTransfer.getData("application/reactflow") as NodeType;
    if (!type) return;
    const id = `${type.toLowerCase()}_${Date.now().toString(36).slice(-4)}`;
    addNode({ id, type, position: { x: e.nativeEvent.offsetX, y: e.nativeEvent.offsetY } });
  }, [addNode]);

  const onDragOver = useCallback((e: DragEvent) => { e.preventDefault(); e.dataTransfer.dropEffect = "move"; }, []);

  const selectedNode = selectedNodeIds.length === 1 ? nodes.find((n) => n.id === selectedNodeIds[0]) : null;

  return (
    <KeyboardManager>
      <DirtyGuard />
      <div data-theme={theme} style={{ display: "flex", flexDirection: "column", height: "100vh", background: "var(--canvas-bg)", color: "var(--text-primary)" }}>
        <TopBar />
        <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
          <NodePalette />
          <div style={{ flex: 1, position: "relative" }} onDrop={onDrop} onDragOver={onDragOver}
            onContextMenu={(e) => { e.preventDefault(); setMenu({ x: e.clientX, y: e.clientY, target: { kind: "canvas" } }); }}>
            {nodes.length === 0 && <EmptyState />}
            <WorkflowCanvas />
            <StickyNoteLayer />
            {drawerOpen && dryRun && <NodeOutputDrawer onClose={() => setDrawerOpen(false)} />}
          </div>
          {selectedNode && <InspectorPanel nodeType={selectedNode.data.nodeType} />}
          {!selectedNode && <div style={{ width: 360, padding: 24, color: "var(--text-secondary)" }}>Select one node to configure</div>}
        </div>
        {menu && <ContextMenu x={menu.x} y={menu.y} target={menu.target} onClose={() => setMenu(null)} />}
      </div>
    </KeyboardManager>
  );
}
