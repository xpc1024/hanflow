export interface CountdownResult {
  remainingSec: number | null;
  phase: "normal" | "warning" | "urgent" | "expired" | "none";
  label: string;
}

export function computeCountdown(pausedAt: string, timeoutSeconds: number | null): CountdownResult {
  if (!timeoutSeconds) return { remainingSec: null, phase: "none", label: "No timeout" };
  const elapsed = (Date.now() - new Date(pausedAt).getTime()) / 1000;
  const remaining = timeoutSeconds - elapsed;
  if (remaining <= 0) return { remainingSec: 0, phase: "expired", label: "Expired" };
  const pct = remaining / timeoutSeconds;
  if (pct <= 0.05) return { remainingSec: remaining, phase: "urgent", label: formatTime(remaining) + ", act now" };
  if (pct <= 0.20) return { remainingSec: remaining, phase: "warning", label: formatTime(remaining) };
  return { remainingSec: remaining, phase: "normal", label: "Remaining: " + formatTime(remaining) };
}

function formatTime(sec: number): string {
  if (sec < 60) return `${Math.ceil(sec)}s`;
  if (sec < 3600) return `${Math.ceil(sec / 60)}m`;
  if (sec < 86400) return `${Math.ceil(sec / 3600)}h`;
  return `${Math.ceil(sec / 86400)}d`;
}
