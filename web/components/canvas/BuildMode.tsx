"use client";

import { useMemo, useState, useCallback, useEffect } from "react";
import { ReactFlow, Background, Controls } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import type { WorkflowDSL } from "@/lib/dsl/types";
import type { Node } from "@xyflow/react";
import { dslToCanvas } from "@/lib/dsl/transform";
import { canvasToDsl } from "@/lib/dsl/transform";
import { layoutDagre } from "@/lib/dsl/layout";
import { PrimitiveNode } from "./PrimitiveNode";
import { NodePalette } from "@/components/toolbar/NodePalette";
import { Inspector } from "@/components/inspector/Inspector";
import { useCanvasStore } from "@/stores/canvasStore";
import type { CanvasNodeData } from "@/lib/dsl/transform";

const nodeTypes = { primitive: PrimitiveNode };

/** Build mode: palette + canvas + inspector + YAML export/import. */
export function BuildMode({ initialDsl }: { initialDsl: WorkflowDSL }) {
  const { nodes, edges, selectedId, setInitial, onNodesChange, onEdgesChange, onConnect, selectNode, updateConfig, deleteNode } =
    useCanvasStore();
  const [yamlOut, setYamlOut] = useState("");

  // Initialize from DSL on mount / when initialDsl changes
  useEffect(() => {
    const { nodes: rawNodes, edges: rawEdges } = dslToCanvas(initialDsl);
    const laid = layoutDagre(rawNodes, rawEdges).map(
      (n) => ({ ...n, type: "primitive" })
    ) as Node<CanvasNodeData>[];
    setInitial(laid, rawEdges);
  }, [initialDsl, setInitial]);

  const selectedNode = useMemo(
    () => nodes.find((n) => n.id === selectedId) ?? null,
    [nodes, selectedId]
  );

  const handleExport = useCallback(() => {
    const dsl = canvasToDsl(nodes, edges, { name: initialDsl.name });
    // Serialize to YAML (simple — production uses js-yaml)
    const lines: string[] = [`name: ${dsl.name}`, "nodes:"];
    for (const n of dsl.nodes) {
      lines.push(`  - id: ${n.id}`);
      lines.push(`    type: ${n.type}`);
      if (n.depends_on && n.depends_on.length > 0) {
        lines.push(`    depends_on: [${n.depends_on.join(", ")}]`);
      }
      if (n.config && Object.keys(n.config).length > 0) {
        lines.push(`    config:`);
        for (const [k, v] of Object.entries(n.config)) {
          lines.push(`      ${k}: ${JSON.stringify(v)}`);
        }
      }
    }
    setYamlOut(lines.join("\n"));
  }, [nodes, edges, initialDsl.name]);

  const handleDelete = useCallback(() => {
    if (selectedId) deleteNode(selectedId);
  }, [selectedId, deleteNode]);

  return (
    <div style={{ display: "flex", height: "100%", minHeight: 600 }}>
      <NodePalette />
      <div style={{ flex: 1, position: "relative" }}>
        <div style={{ position: "absolute", top: 8, right: 8, zIndex: 10, display: "flex", gap: 8 }}>
          <button onClick={handleExport} style={btn}>Export YAML</button>
          <button onClick={handleDelete} disabled={!selectedId} style={btn}>Delete</button>
        </div>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodeClick={(_, n) => selectNode(n.id)}
          onPaneClick={() => selectNode(null)}
          nodeTypes={nodeTypes}
          fitView
        >
          <Background />
          <Controls />
        </ReactFlow>
      </div>
      <Inspector node={selectedNode} onDataChange={updateConfig} />
      {yamlOut && (
        <pre
          style={{
            position: "absolute",
            bottom: 16,
            left: 180,
            right: 320,
            background: "#1e293b",
            color: "#e2e8f0",
            padding: 12,
            borderRadius: 8,
            fontSize: 11,
            fontFamily: "monospace",
            maxHeight: 200,
            overflow: "auto",
            zIndex: 20,
          }}
        >
          {yamlOut}
        </pre>
      )}
    </div>
  );
}

const btn: React.CSSProperties = {
  padding: "6px 12px",
  border: "1px solid #d1d5db",
  borderRadius: 6,
  background: "#fff",
  cursor: "pointer",
  fontSize: 12,
};
