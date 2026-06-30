import { describe, it, expect } from "vitest";
import { layoutDagre } from "@/lib/dsl/layout";
import type { Node, Edge } from "@xyflow/react";

describe("layoutDagre", () => {
  it("assigns distinct positions to each node", () => {
    const nodes: Node[] = [
      { id: "a", position: { x: 0, y: 0 }, data: {} },
      { id: "b", position: { x: 0, y: 0 }, data: {} },
    ];
    const edges: Edge[] = [{ id: "a->b", source: "a", target: "b" }];
    const laid = layoutDagre(nodes, edges);
    const a = laid.find((n) => n.id === "a")!;
    const b = laid.find((n) => n.id === "b")!;
    expect(a.position).not.toEqual(b.position);
  });

  it("preserves node count + ids", () => {
    const nodes: Node[] = [
      { id: "a", position: { x: 0, y: 0 }, data: {} },
      { id: "b", position: { x: 0, y: 0 }, data: {} },
      { id: "c", position: { x: 0, y: 0 }, data: {} },
    ];
    const edges: Edge[] = [
      { id: "a->b", source: "a", target: "b" },
      { id: "b->c", source: "b", target: "c" },
    ];
    const laid = layoutDagre(nodes, edges);
    expect(laid.map((n) => n.id).sort()).toEqual(["a", "b", "c"]);
  });
});
