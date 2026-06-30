"use client";

import { useCallback, useMemo, useState } from "react";
import { ReactFlow, type OnNodesChange, applyNodeChanges } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import type { WorkflowDSL } from "@/lib/dsl/types";
import { dslToCanvas } from "@/lib/dsl/transform";
import { layoutDagre } from "@/lib/dsl/layout";

export function WorkflowCanvas({ dsl }: { dsl: WorkflowDSL }) {
  const initial = useMemo(() => {
    const { nodes, edges } = dslToCanvas(dsl);
    return { nodes: layoutDagre(nodes, edges), edges };
  }, [dsl]);

  const [nodes, setNodes] = useState(initial.nodes);
  const [edges] = useState(initial.edges);

  const onNodesChange: OnNodesChange = useCallback(
    (changes) => setNodes((nds) => applyNodeChanges(changes, nds)),
    []
  );

  return (
    <div style={{ width: "100%", height: 600 }}>
      <ReactFlow nodes={nodes} edges={edges} onNodesChange={onNodesChange} fitView />
    </div>
  );
}
