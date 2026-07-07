"use client";
import { useRef, useState } from "react";
import { highlightTemplate } from "@/lib/dsl/highlight";

interface Props {
  name: string;
  value: string;
  onChange: (v: string) => void;
  nodeColors?: Record<string, string>;
}

function escapeHtml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

export function TemplateField({ name, value, onChange, nodeColors = {} }: Props) {
  const taRef = useRef<HTMLTextAreaElement>(null);
  const highlighted = value.length <= 2000 ? highlightTemplate(value, nodeColors) : escapeHtml(value);

  return (
    <div style={{ marginBottom: 12, position: "relative" }}>
      <label style={{ display: "block", fontSize: 13, color: "var(--text-secondary)", marginBottom: 4 }}>{name}</label>
      <div style={{ position: "relative" }}>
        <div
          aria-hidden
          style={{
            position: "absolute", top: 0, left: 0, right: 0,
            padding: 8, fontFamily: "var(--font-mono)", fontSize: 13,
            whiteSpace: "pre-wrap", wordBreak: "break-word",
            pointerEvents: "none", color: "var(--text-primary)", lineHeight: 1.5,
          }}
          dangerouslySetInnerHTML={{ __html: highlighted + "\u200b" }}
        />
        <textarea
          ref={taRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          rows={4}
          spellCheck={false}
          style={{
            position: "relative", width: "100%", background: "transparent",
            border: "1px solid var(--node-border)", borderRadius: 6,
            color: "transparent", caretColor: "var(--text-primary)",
            padding: 8, fontFamily: "var(--font-mono)", fontSize: 13,
            lineHeight: 1.5, resize: "vertical", outline: "none",
          }}
        />
      </div>
      {value.length > 2000 && (
        <div style={{ color: "var(--warning)", fontSize: 12 }}>
          Template exceeds 2000 chars, highlighting disabled
        </div>
      )}
    </div>
  );
}
