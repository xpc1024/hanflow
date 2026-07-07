"use client";
import { useEffect, useRef, type ReactNode } from "react";
import { useCanvasStore } from "@/stores/canvasStore";

export function KeyboardManager({ children }: { children: ReactNode }) {
  const composingRef = useRef(false);

  useEffect(() => {
    const isEditing = (t: EventTarget | null) => {
      const el = t as HTMLElement | null;
      return (
        !!el &&
        (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.isContentEditable)
      );
    };

    const onDown = (e: KeyboardEvent) => {
      if (composingRef.current) return;
      const editing = isEditing(e.target);
      const s = useCanvasStore.getState();

      if (editing && e.key !== "Escape") return;

      if (e.key === "Delete" || e.key === "Backspace") {
        s.transient.selectedNodeIds.forEach((id) => s.removeNode(id));
        s.transient.selectedEdgeIds.forEach((id) => s.disconnect(id));
      } else if (e.key === "z" && (e.ctrlKey || e.metaKey)) {
        if (e.shiftKey) s.redo();
        else s.undo();
      } else if (e.key === "y" && (e.ctrlKey || e.metaKey)) {
        s.redo();
      } else if (e.key === "a" && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        s.selectNodes(s.nodes.map((n) => n.id));
      } else if (e.key === "c" && (e.ctrlKey || e.metaKey)) {
        s.copySelection();
      } else if (e.key === "v" && (e.ctrlKey || e.metaKey)) {
        s.paste();
      } else if (e.key === "d" && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        s.transient.selectedNodeIds.forEach((id) => {
          const n = s.nodes.find((x) => x.id === id);
          if (n) s.setDisabled(id, !n.data.disabled);
        });
      } else if (e.key === "Escape") {
        s.selectNodes([]);
      }
    };

    const onCompStart = () => {
      composingRef.current = true;
    };
    const onCompEnd = () => {
      composingRef.current = false;
    };

    window.addEventListener("keydown", onDown);
    window.addEventListener("compositionstart", onCompStart);
    window.addEventListener("compositionend", onCompEnd);

    return () => {
      window.removeEventListener("keydown", onDown);
      window.removeEventListener("compositionstart", onCompStart);
      window.removeEventListener("compositionend", onCompEnd);
    };
  }, []);

  return <>{children}</>;
}
