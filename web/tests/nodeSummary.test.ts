import { describe, it, expect } from "vitest";
import { getNodeSummary } from "@/lib/dsl/nodeSummary";

describe("getNodeSummary", () => {
  it("LLM incomplete when no template", () => {
    const s = getNodeSummary("LLM", {});
    expect(s.status).toBe("incomplete");
    expect(s.lines[0]).toMatch(/No prompt/i);
  });
  it("LLM complete shows template preview", () => {
    const s = getNodeSummary("LLM", { template: "Hello world this is long" });
    expect(s.status).toBe("complete");
    expect(s.lines[0]).toContain("Hello world");
  });
  it("Coordinator shows agents", () => {
    const s = getNodeSummary("Coordinator", { sub_agents: ["researcher", "writer"], max_iterations: 5 });
    expect(s.lines.join(" ")).toMatch(/researcher.*writer|Agents/i);
  });
  it("Tool incomplete when no tool", () => {
    const s = getNodeSummary("Tool", {});
    expect(s.status).toBe("incomplete");
  });
});
