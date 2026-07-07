import { describe, it, expect } from "vitest";
import { FALLBACK_NODE_META, mergeMeta } from "@/lib/dsl/nodeMeta";

describe("nodeMeta", () => {
  it("fallback has all 13 types", () => {
    expect(Object.keys(FALLBACK_NODE_META)).toHaveLength(13);
  });

  it("mergeMeta prefers server over fallback", () => {
    const merged = mergeMeta({ LLM: { color: "#server", group: "leaf", icon: "X" } });
    expect(merged.LLM.color).toBe("#server");
    expect(merged.HITL.color).toBe(FALLBACK_NODE_META.HITL.color);
  });
});
