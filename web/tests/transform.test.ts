import { describe, it, expect } from "vitest";
import { dslToCanvas, canvasToDsl } from "@/lib/dsl/transform";
import type { WorkflowDSL } from "@/lib/dsl/types";

describe("dslToCanvas", () => {
  it("converts a single-node DSL to one node and no edges", () => {
    const dsl: WorkflowDSL = {
      name: "w",
      nodes: [{ id: "a", type: "LLM", config: { template: "hi" } }],
    };
    const { nodes, edges } = dslToCanvas(dsl);
    expect(nodes).toHaveLength(1);
    expect(nodes[0].id).toBe("a");
    expect(nodes[0].data.label).toBe("a");
    expect(edges).toHaveLength(0);
  });

  it("converts depends_on into edges (a→b when b depends_on a)", () => {
    const dsl: WorkflowDSL = {
      name: "w",
      nodes: [
        { id: "a", type: "LLM" },
        { id: "b", type: "LLM", depends_on: ["a"] },
      ],
    };
    const { edges } = dslToCanvas(dsl);
    expect(edges).toHaveLength(1);
    expect(edges[0].source).toBe("a");
    expect(edges[0].target).toBe("b");
  });

  it("preserves node type + config in node.data", () => {
    const dsl: WorkflowDSL = {
      name: "w",
      nodes: [{ id: "a", type: "HITL", config: { actions: ["approve"] } }],
    };
    const { nodes } = dslToCanvas(dsl);
    expect(nodes[0].data.nodeType).toBe("HITL");
    expect(nodes[0].data.config).toEqual({ actions: ["approve"] });
  });
});

describe("canvasToDsl", () => {
  it("converts nodes + edges back to a WorkflowDSL", () => {
    const dsl: WorkflowDSL = {
      name: "w",
      nodes: [
        { id: "a", type: "LLM" },
        { id: "b", type: "LLM", depends_on: ["a"] },
      ],
    };
    const { nodes, edges } = dslToCanvas(dsl);
    const back = canvasToDsl(nodes, edges, { name: "w" });
    expect(back.nodes).toHaveLength(2);
    const b = back.nodes.find((n) => n.id === "b")!;
    expect(b.depends_on).toEqual(["a"]);
  });
});

describe("round-trip invariant", () => {
  it("canvasToDsl(dslToCanvas(x)).nodes === x.nodes for a linear graph", () => {
    const dsl: WorkflowDSL = {
      name: "w",
      nodes: [
        { id: "a", type: "LLM", config: { template: "1" } },
        { id: "b", type: "Tool", depends_on: ["a"], config: { tool: "echo.say" } },
        { id: "c", type: "LLM", depends_on: ["b"], config: { template: "3" } },
      ],
    };
    const { nodes, edges } = dslToCanvas(dsl);
    const back = canvasToDsl(nodes, edges, { name: dsl.name });
    expect(back.nodes).toEqual(dsl.nodes);
  });
});
