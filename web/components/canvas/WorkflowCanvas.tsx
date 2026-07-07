"use client";
import { useCallback } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  ReactFlowProvider,
  BackgroundVariant,
  applyNodeChanges,
  type OnConnect,
  type OnNodesChange,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useCanvasStore } from "@/stores/canvasStore";
import { canConnect } from "@/lib/dsl/ports";
import { CanvasNode } from "./CanvasNode";

const nodeTypes = { canvasNode: CanvasNode };

interface Props {
  readOnly?: boolean;
}

export function WorkflowCanvas({ readOnly = false }: Props) {
  const { nodes, edges, connect, moveNode, selectNodes } = useCanvasStore();

  const onConnect: OnConnect = useCallback(
    (c) => {
      if (readOnly) return;
      const r = canConnect(c.source, c.target, useCanvasStore.getState().edges);
      if (r.ok) connect(c.source, c.target);
    },
    [connect, readOnly]
  );

  const onNodesChange: OnNodesChange = useCallback(
    (changes) => {
      if (readOnly) return;
      const store = useCanvasStore.getState();
      const updated = applyNodeChanges(changes, store.nodes) as typeof store.nodes;
      changes.forEach((ch) => {
        if (ch.type === "position" && ch.dragging === false && ch.position) {
          moveNode(ch.id, ch.position, true);
        }
        if (ch.type === "select" && ch.id) {
          selectNodes(ch.selected ? [ch.id] : []);
        }
      });
      useCanvasStore.setState({ nodes: updated });
    },
    [moveNode, selectNodes, readOnly]
  );

  return (
    <ReactFlowProvider>
      <div style={{ width: "100%", height: "100%" }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          onConnect={onConnect}
          onNodesChange={onNodesChange}
          nodesDraggable={!readOnly}
          nodesConnectable={!readOnly}
          elementsSelectable={!readOnly}
          fitView
          defaultEdgeOptions={{
            style: { strokeWidth: 2, stroke: "var(--text-secondary)" },
          }}
          proOptions={{ hideAttribution: true }}
        >
          <Background variant={BackgroundVariant.Dots} gap={16} />
          <Controls />
          <MiniMap
            nodeColor={() => "#6b7280"}
            style={{ background: "var(--panel-bg)" }}
          />
        </ReactFlow>
      </div>
    </ReactFlowProvider>
  );
}
