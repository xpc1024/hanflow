import { describe, it, expect } from "vitest";
import { canvasToDsl } from "@/lib/dsl/transform";
import type { Node, Edge } from "@xyflow/react";
import type { CanvasNodeData } from "@/lib/dsl/transform";

describe("canvasToDsl edit flow", () => {
  it("converts manually-added nodes + connected edges into valid DSL", () => {
    const nodes: Node<CanvasNodeData>[] = [
      { id: "llm-1", type: "primitive", position: { x: 0, y: 0 }, data: { label: "llm-1", nodeType: "LLM", config: { template: "hi" } } },
      { id: "tool-2", type: "primitive", position: { x: 0, y: 100 }, data: { label: "tool-2", nodeType: "Tool", config: { tool: "echo.say" } } },
    ];
    const edges: Edge[] = [{ id: "llm-1->tool-2", source: "llm-1", target: "tool-2" }];
    const dsl = canvasToDsl(nodes, edges, { name: "edited" });
    expect(dsl.name).toBe("edited");
    expect(dsl.nodes).toHaveLength(2);
    const tool = dsl.nodes.find((n) => n.id === "tool-2")!;
    expect(tool.type).toBe("Tool");
    expect(tool.depends_on).toEqual(["llm-1"]);
    expect(tool.config).toEqual({ tool: "echo.say" });
  });

  it("handles a node with no edges (no depends_on)", () => {
    const nodes: Node<CanvasNodeData>[] = [
      { id: "solo", type: "primitive", position: { x: 0, y: 0 }, data: { label: "solo", nodeType: "HITL", config: {} } },
    ];
    const dsl = canvasToDsl(nodes, [], { name: "w" });
    expect(dsl.nodes[0].depends_on).toBeUndefined();
  });
});
