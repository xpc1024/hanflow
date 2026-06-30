"use client";

import { useCallback, useMemo, useState } from "react";
import { ReactFlow, type Node, type OnNodesChange, applyNodeChanges } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import type { WorkflowDSL } from "@/lib/dsl/types";
import { dslToCanvas } from "@/lib/dsl/transform";
import { layoutDagre } from "@/lib/dsl/layout";
import { PrimitiveNode } from "./PrimitiveNode";

const nodeTypes = { primitive: PrimitiveNode };

export function WorkflowCanvas({ dsl }: { dsl: WorkflowDSL }) {
  const initial = useMemo(() => {
    const { nodes, edges } = dslToCanvas(dsl);
    // Tag each node as "primitive" so RF renders PrimitiveNode
    const typed: Node[] = layoutDagre(nodes, edges).map((n) => ({
      ...n,
      type: "primitive",
    }));
    return { nodes: typed, edges };
  }, [dsl]);

  const [nodes, setNodes] = useState<Node[]>(initial.nodes);
  const [edges] = useState(initial.edges);

  const onNodesChange: OnNodesChange = useCallback(
    (changes) => setNodes((nds) => applyNodeChanges(changes, nds)),
    []
  );

  return (
    <div style={{ width: "100%", height: 600 }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        nodeTypes={nodeTypes}
        fitView
      />
    </div>
  );
}
