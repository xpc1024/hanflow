import { describe, it, expect } from "vitest";
import { validateWorkflow } from "@/lib/dsl/validateWorkflow";
import type { WorkflowDSL } from "@/lib/dsl/types";

describe("validateWorkflow", () => {
  it("valid linear graph", () => {
    const dsl: WorkflowDSL = { name: "w", nodes: [
      { id: "a", type: "LLM", config: { template: "hi" } },
      { id: "b", type: "Tool", depends_on: ["a"], config: { tool: "x" } },
    ]};
    expect(validateWorkflow(dsl).valid).toBe(true);
  });
  it("rejects duplicate ids", () => {
    expect(validateWorkflow({ name: "w", nodes: [{ id: "a", type: "LLM" }, { id: "a", type: "LLM" }] }).valid).toBe(false);
  });
  it("rejects cycle", () => {
    expect(validateWorkflow({ name: "w", nodes: [
      { id: "a", type: "LLM", depends_on: ["b"] }, { id: "b", type: "LLM", depends_on: ["a"] },
    ]}).valid).toBe(false);
  });
  it("rejects zero entries", () => {
    expect(validateWorkflow({ name: "w", nodes: [
      { id: "a", type: "LLM", depends_on: ["b"] }, { id: "b", type: "LLM", depends_on: ["a"] },
    ]}).errors.some((e) => /entry/i.test(e.message))).toBe(true);
  });
});
