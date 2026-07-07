import { describe, it, expect } from "vitest";
import { dslToCanvas, canvasToDsl } from "@/lib/dsl/transform";
import type { WorkflowDSL } from "@/lib/dsl/types";

const fullNode = (overrides: Partial<WorkflowDSL["nodes"][0]> = {}): WorkflowDSL["nodes"][0] => ({
  id: "a", type: "LLM", config: { template: "hi" }, ...overrides,
});

describe("dslToCanvas", () => {
  it("single node to 1 node 0 edges", () => {
    const { nodes, edges } = dslToCanvas({ name: "w", nodes: [fullNode()] });
    expect(nodes).toHaveLength(1);
    expect(nodes[0].id).toBe("a");
    expect(edges).toHaveLength(0);
  });

  it("depends_on to edges (source=dep, target=dependent)", () => {
    const { edges } = dslToCanvas({
      name: "w",
      nodes: [fullNode({ id: "a" }), fullNode({ id: "b", depends_on: ["a"], type: "Tool" })],
    });
    expect(edges).toHaveLength(1);
    expect(edges[0]).toMatchObject({ source: "a", target: "b" });
  });

  it("reads positions from metadata.canvas", () => {
    const { nodes } = dslToCanvas({
      name: "w",
      nodes: [fullNode()],
      metadata: { canvas: { positions: { a: { x: 10, y: 20 } } } },
    } as WorkflowDSL);
    expect(nodes[0].position).toEqual({ x: 10, y: 20 });
  });

  it("default position (0,0) when no metadata", () => {
    const { nodes } = dslToCanvas({ name: "w", nodes: [fullNode()] });
    expect(nodes[0].position).toEqual({ x: 0, y: 0 });
  });
});

describe("round-trip: canvasToDsl(dslToCanvas(x)).nodes === x.nodes", () => {
  it("linear graph with full fields", () => {
    const dsl: WorkflowDSL = {
      name: "w",
      nodes: [
        { id: "a", type: "LLM", config: { template: "1" } },
        { id: "b", type: "Tool", depends_on: ["a"], config: { tool: "echo.say" } },
        { id: "c", type: "HITL", depends_on: ["b"], condition: "b.action == approve", sensitivity: "confidential", disabled: true },
      ],
    };
    const { nodes, edges } = dslToCanvas(dsl);
    const back = canvasToDsl(nodes, edges, { name: dsl.name });
    expect(back.nodes).toEqual(dsl.nodes);
  });

  it("preserves on_error + retry + timeout", () => {
    const dsl: WorkflowDSL = {
      name: "w",
      nodes: [
        { id: "a", type: "LLM", on_error: { type: "retry", max_retries: 3 }, retry: { max_attempts: 2 }, timeout_seconds: 60 },
      ],
    };
    const { nodes, edges } = dslToCanvas(dsl);
    const back = canvasToDsl(nodes, edges, { name: dsl.name });
    expect(back.nodes).toEqual(dsl.nodes);
  });

  it("parallel fan-out + merge", () => {
    const dsl: WorkflowDSL = {
      name: "w",
      nodes: [
        { id: "a", type: "LLM" },
        { id: "b", type: "Tool", depends_on: ["a"] },
        { id: "c", type: "Tool", depends_on: ["a"] },
        { id: "d", type: "LLM", depends_on: ["b", "c"] },
      ],
    };
    const { nodes, edges } = dslToCanvas(dsl);
    const back = canvasToDsl(nodes, edges, { name: dsl.name });
    expect(back.nodes).toEqual(dsl.nodes);
  });
});

describe("notes isolation", () => {
  it("notes only in metadata.canvas.notes, not in nodes", () => {
    const dsl: WorkflowDSL = {
      name: "w",
      nodes: [fullNode()],
      metadata: { canvas: { notes: [{ id: "n1", x: 0, y: 0, width: 160, height: 100, text: "hi", color: "yellow" }] } },
    } as WorkflowDSL;
    const { nodes } = dslToCanvas(dsl);
    expect(nodes.every((n) => n.id !== "n1")).toBe(true);
  });
});
