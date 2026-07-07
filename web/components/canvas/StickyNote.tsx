"use client";
import { useCanvasStore } from "@/stores/canvasStore";
import type { CanvasNote } from "@/lib/dsl/transform";

const NOTE_COLORS: Record<string, { bg: string; text: string }> = {
  yellow: { bg: "var(--note-yellow)", text: "var(--note-yellow-text)" },
  green: { bg: "var(--note-green)", text: "var(--note-green-text)" },
  blue: { bg: "var(--note-blue)", text: "var(--note-blue-text)" },
  pink: { bg: "var(--note-pink)", text: "var(--note-pink-text)" },
};

interface Props {
  note: CanvasNote;
}

export function StickyNote({ note }: Props) {
  const { updateNote, removeNote } = useCanvasStore();
  const colors = NOTE_COLORS[note.color] ?? NOTE_COLORS.yellow;

  return (
    <div
      style={{
        position: "absolute",
        left: note.x,
        top: note.y,
        width: note.width,
        minHeight: note.height,
        background: colors.bg,
        color: colors.text,
        borderRadius: 8,
        padding: 8,
        fontSize: 13,
        fontFamily: "var(--font-mono)",
        boxShadow: "0 2px 8px rgba(0,0,0,.2)",
        resize: "both",
        overflow: "auto",
      }}
    >
      <div
        contentEditable
        suppressContentEditableWarning
        onBlur={(e) => {
          const text = e.target.textContent ?? "";
          if (text.trim() === "") {
            removeNote(note.id);
          } else {
            updateNote(note.id, { text });
          }
        }}
        style={{ outline: "none", minHeight: 40 }}
      >
        {note.text}
      </div>
      <div style={{ display: "flex", gap: 4, marginTop: 4 }}>
        {Object.entries(NOTE_COLORS).map(([c, cl]) => (
          <button
            key={c}
            onClick={() => updateNote(note.id, { color: c as CanvasNote["color"] })}
            style={{
              width: 12,
              height: 12,
              borderRadius: "50%",
              background: cl.bg,
              border: note.color === c ? "2px solid #fff" : "1px solid rgba(0,0,0,.2)",
              cursor: "pointer",
            }}
          />
        ))}
      </div>
    </div>
  );
}

export function StickyNoteLayer() {
  const notes = useCanvasStore((s) => s.meta.notes);
  if (notes.length === 0) return null;
  return (
    <div style={{ position: "absolute", inset: 0, pointerEvents: "none", zIndex: 5 }}>
      {notes.map((n) => (
        <div key={n.id} style={{ pointerEvents: "auto" }}>
          <StickyNote note={n} />
        </div>
      ))}
    </div>
  );
}
