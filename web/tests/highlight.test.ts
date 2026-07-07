import { describe, it, expect } from "vitest";
import { highlightTemplate } from "@/lib/dsl/highlight";

describe("highlightTemplate", () => {
  it("wraps known ref in colored span", () => {
    const r = highlightTemplate("Hi {{intake.content}}", { intake: "#3b82f6" });
    expect(r).toContain("#3b82f6");
    expect(r).toContain("intake.content");
  });
  it("unknown ref red", () => {
    const r = highlightTemplate("{{intek.x}}", { intake: "#3b82f6" });
    expect(r).toMatch(/red|#ef4444/i);
  });
  it("escapes HTML", () => {
    const r = highlightTemplate("<script>x</script>", {});
    expect(r).not.toContain("<script>");
  });
});
