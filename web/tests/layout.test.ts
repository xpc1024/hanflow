import { describe, it, expect } from "vitest";
import { layoutDagre, snapToGrid } from "@/lib/dsl/layout";
import type { Edge, Node } from "@xyflow/react";

describe("layoutDagre", () => {
  it("assigns distinct positions (LR)", () => {
    const nodes: Node[] = [
      { id: "a", position: { x: 0, y: 0 }, data: {} },
      { id: "b", position: { x: 0, y: 0 }, data: {} },
    ];
    const edges: Edge[] = [{ id: "a->b", source: "a", target: "b" }];
    const laid = layoutDagre(nodes, edges, { direction: "LR" });
    expect(laid.find((n) => n.id === "a")!.position).not.toEqual(
      laid.find((n) => n.id === "b")!.position
    );
  });

  it("preserves node count + ids", () => {
    const nodes = [
      { id: "a", position: { x: 0, y: 0 }, data: {} },
      { id: "b", position: { x: 0, y: 0 }, data: {} },
      { id: "c", position: { x: 0, y: 0 }, data: {} },
    ];
    const edges = [
      { id: "a->b", source: "a", target: "b" },
      { id: "b->c", source: "b", target: "c" },
    ];
    const laid = layoutDagre(nodes, edges);
    expect(laid.map((n) => n.id).sort()).toEqual(["a", "b", "c"]);
  });
});

describe("snapToGrid", () => {
  it("snaps to 8px grid", () => {
    expect(snapToGrid({ x: 13, y: 17 }, 8)).toEqual({ x: 16, y: 16 });
    expect(snapToGrid({ x: 0, y: 0 }, 8)).toEqual({ x: 0, y: 0 });
  });
});
