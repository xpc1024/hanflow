"use client";
import { useCanvasStore } from "@/stores/canvasStore";
import { en } from "@/lib/i18n/en";

interface Props {
  x: number;
  y: number;
  target: { kind: "canvas" } | { kind: "node"; nodeId: string };
  onClose: () => void;
}

export function ContextMenu({ x, y, target, onClose }: Props) {
  const store = useCanvasStore();

  const canvasItems = [
    { label: en.menu.paste, action: () => store.paste(), disabled: !store.transient.clipboard },
    { label: en.menu.selectAll, action: () => store.selectNodes(store.nodes.map((n) => n.id)) },
    { label: en.menu.autoAlign, action: () => store.alignAll() },
    { label: en.menu.snapToGrid, action: () => store.snapToGridAll() },
    {
      label: en.menu.addNote,
      action: () =>
        store.addNote({
          id: `note_${Date.now().toString(36)}`,
          x,
          y,
          width: 160,
          height: 100,
          text: "",
          color: "yellow",
        }),
    },
  ];

  const nodeItems =
    target.kind === "node"
      ? [
          {
            label: en.menu.copy,
            action: () => {
              store.selectNodes([target.nodeId]);
              store.copySelection();
            },
          },
          { label: en.menu.delete, action: () => store.removeNode(target.nodeId) },
          {
            label: en.menu.disable,
            action: () => {
              const n = store.nodes.find((n) => n.id === target.nodeId);
              if (n) store.setDisabled(target.nodeId, !n.data.disabled);
            },
          },
        ]
      : [];

  const items = target.kind === "canvas" ? canvasItems : nodeItems;

  return (
    <div
      style={{
        position: "fixed",
        left: x,
        top: y,
        zIndex: 100,
        background: "var(--panel-bg)",
        border: "1px solid var(--panel-border)",
        borderRadius: 8,
        padding: 4,
        minWidth: 200,
      }}
      onClick={onClose}
    >
      {items.map((it, i) => (
        <button
          key={i}
          disabled={"disabled" in it ? it.disabled : false}
          onClick={it.action}
          style={{
            display: "block",
            width: "100%",
            textAlign: "left",
            padding: "6px 12px",
            background: "transparent",
            border: "none",
            color:
              "disabled" in it && it.disabled
                ? "var(--text-disabled)"
                : "var(--text-primary)",
            cursor: "pointer",
            fontSize: 13,
          }}
        >
          {it.label}
        </button>
      ))}
    </div>
  );
}
