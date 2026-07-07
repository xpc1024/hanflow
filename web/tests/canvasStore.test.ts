import { describe, it, expect, beforeEach } from "vitest";
import { useCanvasStore } from "@/stores/canvasStore";

describe("canvasStore", () => {
  beforeEach(() => useCanvasStore.getState().reset());

  it("addNode adds a node + pushes history", () => {
    const { addNode } = useCanvasStore.getState();
    addNode({ id: "a", type: "LLM", position: { x: 0, y: 0 } });
    expect(useCanvasStore.getState().nodes).toHaveLength(1);
    expect(useCanvasStore.getState().history.canUndo()).toBe(true);
  });

  it("connect adds edge", () => {
    const { addNode, connect } = useCanvasStore.getState();
    addNode({ id: "a", type: "LLM", position: { x: 0, y: 0 } });
    addNode({ id: "b", type: "LLM", position: { x: 100, y: 0 } });
    expect(connect("a", "b")).toBe(true);
    expect(useCanvasStore.getState().edges).toHaveLength(1);
  });

  it("connect rejects self-loop", () => {
    const { addNode, connect } = useCanvasStore.getState();
    addNode({ id: "a", type: "LLM", position: { x: 0, y: 0 } });
    expect(connect("a", "a")).toBe(false);
    expect(useCanvasStore.getState().edges).toHaveLength(0);
  });

  it("removeNode removes node + connected edges", () => {
    const { addNode, connect, removeNode } = useCanvasStore.getState();
    addNode({ id: "a", type: "LLM", position: { x: 0, y: 0 } });
    addNode({ id: "b", type: "LLM", position: { x: 100, y: 0 } });
    connect("a", "b");
    removeNode("a");
    expect(useCanvasStore.getState().nodes).toHaveLength(1);
    expect(useCanvasStore.getState().edges).toHaveLength(0);
  });

  it("setDisabled toggles disabled", () => {
    const { addNode, setDisabled } = useCanvasStore.getState();
    addNode({ id: "a", type: "LLM", position: { x: 0, y: 0 } });
    setDisabled("a", true);
    expect(useCanvasStore.getState().nodes[0].data.disabled).toBe(true);
  });

  it("undo restores previous state", () => {
    const { addNode, undo } = useCanvasStore.getState();
    addNode({ id: "a", type: "LLM", position: { x: 0, y: 0 } });
    undo();
    expect(useCanvasStore.getState().nodes).toHaveLength(0);
  });

  it("redo re-applies", () => {
    const { addNode, undo, redo } = useCanvasStore.getState();
    addNode({ id: "a", type: "LLM", position: { x: 0, y: 0 } });
    undo();
    redo();
    expect(useCanvasStore.getState().nodes).toHaveLength(1);
  });

  it("addNote adds to meta.notes", () => {
    const { addNote } = useCanvasStore.getState();
    addNote({ id: "n1", x: 10, y: 10, width: 160, height: 100, text: "hi", color: "yellow" });
    expect(useCanvasStore.getState().meta.notes).toHaveLength(1);
  });

  it("renameNode changes id + updates edges", () => {
    const { addNode, connect, renameNode } = useCanvasStore.getState();
    addNode({ id: "a", type: "LLM", position: { x: 0, y: 0 } });
    addNode({ id: "b", type: "LLM", position: { x: 100, y: 0 } });
    connect("a", "b");
    renameNode("a", "renamed");
    expect(useCanvasStore.getState().nodes.find((n) => n.id === "renamed")).toBeTruthy();
    expect(useCanvasStore.getState().edges[0].source).toBe("renamed");
  });
});
