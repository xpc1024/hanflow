import { describe, it, expect } from "vitest";
import { canConnect } from "@/lib/dsl/ports";
import type { Edge } from "@xyflow/react";

describe("canConnect", () => {
  it("rejects self-loop", () => {
    const r = canConnect("a", "a", []);
    expect(r.ok).toBe(false);
    expect(r.reason).toMatch(/itself/);
  });

  it("rejects duplicate edge", () => {
    const edges: Edge[] = [{ id: "a->b", source: "a", target: "b" }];
    const r = canConnect("a", "b", edges);
    expect(r.ok).toBe(false);
    expect(r.reason).toMatch(/already exists/);
  });

  it("rejects cycle", () => {
    const edges: Edge[] = [{ id: "a->b", source: "a", target: "b" }];
    const r = canConnect("b", "a", edges);
    expect(r.ok).toBe(false);
    expect(r.reason).toMatch(/cycle/);
  });

  it("accepts valid new edge", () => {
    const r = canConnect("a", "b", []);
    expect(r.ok).toBe(true);
  });
});
