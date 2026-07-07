import { describe, it, expect } from "vitest";
import { History } from "@/lib/dsl/history";

describe("History", () => {
  it("push/undo/redo with manual redo push", () => {
    const h = new History<number>(3);
    h.push(1); // state before edit
    h.push(2); // state before 2nd edit
    // undo: pop 2, push current(3 not set... just test API)
    const undone = h.undoPop();
    expect(undone).toBe(2);
    h.pushRedo(99); // push "current state" to redo
    expect(h.redoPop()).toBe(99);
  });

  it("undo after new op clears redo", () => {
    const h = new History<number>(3);
    h.push(1);
    h.push(2);
    h.undoPop();
    h.push(3); // new op clears redo
    expect(h.canRedo()).toBe(false);
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
