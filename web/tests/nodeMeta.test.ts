import { describe, it, expect } from "vitest";
import { NODE_META, CONFIG_SCHEMA } from "@/lib/dsl/nodeMeta";
import type { NodeType } from "@/lib/dsl/types";

const ALL_TYPES: NodeType[] = [
  "Sequential", "Parallel", "Loop", "Branch", "HITL",
  "LLM", "Tool", "Research", "Execution",
  "Coordinator",
  "Memory", "Subworkflow",
  "Knowledge",
];

describe("NODE_META", () => {
  it("has metadata for all 13 node types", () => {
    for (const t of ALL_TYPES) {
      expect(NODE_META[t], `missing meta for ${t}`).toBeDefined();
      expect(NODE_META[t].color).toMatch(/^#/);
      expect(NODE_META[t].label).toBeTruthy();
    }
    expect(Object.keys(NODE_META)).toHaveLength(13);
  });

  it("assigns the documented colors (LLM blue, HITL yellow, Coordinator purple)", () => {
    expect(NODE_META.LLM.color).toBe("#3b82f6");
    expect(NODE_META.HITL.color).toBe("#eab308");
    expect(NODE_META.Coordinator.color).toBe("#a855f7");
  });
});

describe("CONFIG_SCHEMA", () => {
  it("has a schema for LLM with template field", () => {
    expect(CONFIG_SCHEMA.LLM.template).toBe("string");
  });

  it("marks optional fields with ?", () => {
    expect(CONFIG_SCHEMA.LLM.model).toBe("string?");
  });
});
