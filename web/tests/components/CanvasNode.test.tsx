import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { CanvasNode } from "@/components/canvas/CanvasNode";

vi.mock("@xyflow/react", () => ({
  Handle: ({ type }: { type: string }) => <div data-testid={`handle-${type}`} />,
  Position: { Left: "left", Right: "right" },
}));

describe("CanvasNode", () => {
  it("renders type label", () => {
    render(
      <CanvasNode
        id="a"
        data={{ label: "intake", nodeType: "LLM" }}
        selected={false}
      />
    );
    expect(screen.getByText("LLM")).toBeTruthy();
  });

  it("shows hover actions on mouseenter", () => {
    render(
      <CanvasNode
        id="a"
        data={{ label: "a", nodeType: "LLM" }}
        selected={false}
      />
    );
    expect(screen.queryByLabelText("Add next node")).toBeNull();
    fireEvent.mouseEnter(screen.getByTestId("canvas-node-a"));
    expect(screen.getByLabelText("Add next node")).toBeTruthy();
    expect(screen.getByLabelText("Copy node")).toBeTruthy();
    expect(screen.getByLabelText("Delete node")).toBeTruthy();
  });

  it("shows disabled badge when disabled", () => {
    render(
      <CanvasNode
        id="a"
        data={{ label: "a", nodeType: "LLM", disabled: true }}
        selected={false}
      />
    );
    expect(screen.getByText("Disabled")).toBeTruthy();
  });

  it("renders input + output handles", () => {
    render(
      <CanvasNode
        id="a"
        data={{ label: "a", nodeType: "LLM" }}
        selected={false}
      />
    );
    expect(screen.getByTestId("handle-target")).toBeTruthy();
    expect(screen.getByTestId("handle-source")).toBeTruthy();
  });
});
