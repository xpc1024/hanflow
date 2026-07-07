"use client";
import { en } from "@/lib/i18n/en";

interface Props { invalid?: boolean; incomplete?: boolean; disabled?: boolean; dynamic?: boolean; confidential?: boolean; }

const PRIORITY = ["invalid", "incomplete", "disabled", "dynamic", "confidential"] as const;
const STYLE: Record<string, { bg: string; label: string; icon: string }> = {
  invalid: { bg: "var(--danger)", label: en.node ? "" : "", icon: "⛔" },
  incomplete: { bg: "var(--warning)", label: "", icon: "⚠" },
  disabled: { bg: "var(--text-disabled)", label: "", icon: "⏸" },
  dynamic: { bg: "#a855f7", label: "", icon: "🟣" },
  confidential: { bg: "#0ea5e9", label: "", icon: "🔒" },
};
const TOOLTIPS: Record<string, string> = {
  invalid: "Configuration has errors",
  incomplete: "Required fields missing",
  disabled: "Node is disabled",
  dynamic: "Dynamic node",
  confidential: "Sensitive data",
};

export function NodeBadges(props: Props) {
  const active = PRIORITY.filter((k) => props[k]);
  const top2 = active.slice(0, 2);
  if (top2.length === 0) return null;
  return (
    <div
      style={{ position: "absolute", top: -6, left: -6, display: "flex", gap: 2, zIndex: 5 }}
      title={active.map((k) => TOOLTIPS[k]).join(", ")}
    >
      {top2.map((k) => (
        <span
          key={k}
          style={{
            width: 14, height: 14, borderRadius: "50%", background: STYLE[k].bg,
            display: "flex", alignItems: "center", justifyContent: "center", fontSize: 9,
          }}
        >
          {STYLE[k].icon}
        </span>
      ))}
    </div>
  );
}
