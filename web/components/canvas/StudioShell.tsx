"use client";
import { useState, useCallback, type DragEvent } from "react";
import { NodePalette } from "./NodePalette";
import { TopBar } from "./TopBar";
import { WorkflowCanvas } from "./WorkflowCanvas";
import { EmptyState } from "./EmptyState";
import { ContextMenu } from "./ContextMenu";
import { KeyboardManager } from "./KeyboardManager";
import { StickyNoteLayer } from "./StickyNote";
import { useCanvasStore } from "@/stores/canvasStore";
import { useUiStore } from "@/stores/uiStore";
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

  const onDrop = useCallback(
    (e: DragEvent) => {
      e.preventDefault();
      const type = e.dataTransfer.getData("application/reactflow") as NodeType;
      if (!type) return;
      const id = `${type.toLowerCase()}_${Date.now().toString(36).slice(-4)}`;
      addNode({
        id,
        type,
        position: { x: e.nativeEvent.offsetX, y: e.nativeEvent.offsetY },
      });
    },
    [addNode]
  );

  const onDragOver = useCallback((e: DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
  }, []);

  return (
    <KeyboardManager>
      <div
        data-theme={theme}
        style={{
          display: "flex",
          flexDirection: "column",
          height: "100vh",
          background: "var(--canvas-bg)",
          color: "var(--text-primary)",
        }}
      >
        <TopBar />
        <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
          <NodePalette />
          <div
            style={{ flex: 1, position: "relative" }}
            onDrop={onDrop}
            onDragOver={onDragOver}
            onContextMenu={(e) => {
              e.preventDefault();
              setMenu({ x: e.clientX, y: e.clientY, target: { kind: "canvas" } });
            }}
          >
            {nodes.length === 0 && <EmptyState />}
            <WorkflowCanvas />
            <StickyNoteLayer />
          </div>
        </div>
        {menu && (
          <ContextMenu x={menu.x} y={menu.y} target={menu.target} onClose={() => setMenu(null)} />
        )}
      </div>
    </KeyboardManager>
  );
}
