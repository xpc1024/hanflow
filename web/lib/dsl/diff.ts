import { diffLines } from "diff";

export interface DiffLine { type: "added" | "removed" | "context"; text: string; }

export function lineDiff(oldText: string, newText: string): DiffLine[] {
  const changes = diffLines(oldText, newText);
  const result: DiffLine[] = [];
  for (const part of changes) {
    const type = part.added ? "added" : part.removed ? "removed" : "context";
    const lines = part.value.split("\n");
    if (lines.length > 0 && lines[lines.length - 1] === "") lines.pop();
    for (const line of lines) result.push({ type, text: line });
  }
  return result;
}

export function truncate(text: string, maxBytes: number = 10240): { text: string; truncated: boolean } {
  if (text.length <= maxBytes) return { text, truncated: false };
  return { text: text.slice(0, maxBytes), truncated: true };
}
