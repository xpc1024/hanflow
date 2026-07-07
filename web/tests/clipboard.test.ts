import { describe, it, expect } from "vitest";
import { remapIds } from "@/lib/dsl/clipboard";

describe("remapIds", () => {
  it("appends _copy1 on conflict", () => {
    const r = remapIds(["a", "b"], new Set(["a", "b"]));
    expect(r.mapping.a).toBe("a_copy1");
    expect(r.mapping.b).toBe("b_copy1");
  });

  it("increments on repeated paste", () => {
    const r = remapIds(["a"], new Set(["a", "a_copy1"]));
    expect(r.mapping.a).toBe("a_copy2");
  });

  it("no change if no conflict", () => {
    const r = remapIds(["x"], new Set(["a"]));
    expect(r.mapping.x).toBe("x");
  });
});
