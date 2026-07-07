import { describe, it, expect } from "vitest";
import { History } from "@/lib/dsl/history";

describe("History", () => {
  it("push/undo/redo", () => {
    const h = new History<number>(3);
    h.push(1);
    h.push(2);
    expect(h.undoPop()).toBe(2);
    expect(h.redoPop()).toBe(2);
  });

  it("undo after new op clears redo", () => {
    const h = new History<number>(3);
    h.push(1);
    h.push(2);
    h.undoPop();
    h.push(3);
    expect(h.redoPop()).toBeNull();
  });

  it("max 3 drops oldest", () => {
    const h = new History<number>(3);
    h.push(1);
    h.push(2);
    h.push(3);
    h.push(4);
    expect(h.undoPop()).toBe(4);
    expect(h.undoPop()).toBe(3);
    expect(h.undoPop()).toBe(2);
    expect(h.undoPop()).toBeNull();
  });
});
