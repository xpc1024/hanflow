import { describe, it, expect } from "vitest";
import { checkConfig, checkReferences } from "@/lib/dsl/validate";

describe("checkConfig", () => {
  it("LLM: empty template+prompt -> alternatives fail", () => {
    const r = checkConfig("LLM", {}, { alternatives: [["template", "prompt"]] });
    expect(r.valid).toBe(false);
  });
  it("LLM: has template -> valid", () => {
    const r = checkConfig("LLM", { template: "hi" }, { alternatives: [["template", "prompt"]] });
    expect(r.valid).toBe(true);
  });
  it("Tool: no tool -> required fail", () => {
    const r = checkConfig("Tool", {}, { required: ["tool"] });
    expect(r.valid).toBe(false);
  });
  it("Loop: max_iterations 2000 -> range fail", () => {
    const r = checkConfig("Loop", { max_iterations: 2000 }, { ranges: { max_iterations: { min: 1, max: 1000 } } });
    expect(r.valid).toBe(false);
  });
  it("HITL: empty actions array -> non_empty_if_set fail", () => {
    const r = checkConfig("HITL", { actions: [] }, { non_empty_if_set: ["actions"] });
    expect(r.valid).toBe(false);
  });
  it("HITL: actions undefined -> valid", () => {
    const r = checkConfig("HITL", {}, { non_empty_if_set: ["actions"] });
    expect(r.valid).toBe(true);
  });
});

describe("checkReferences", () => {
  it("valid reference", () => {
    const r = checkReferences("Hello {{intake.content}}", new Set(["intake"]));
    expect(r.valid).toBe(true);
  });
  it("unresolved reference", () => {
    const r = checkReferences("Hello {{intek.x}}", new Set(["intake"]));
    expect(r.valid).toBe(false);
    expect(r.unresolved).toContain("intek");
  });
  it("no refs -> valid", () => {
    const r = checkReferences("plain text", new Set(["a"]));
    expect(r.valid).toBe(true);
  });
});
