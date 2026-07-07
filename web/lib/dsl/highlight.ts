const REF_RE = /\{\{\s*([A-Za-z_][\w-]*)\.([\w-]+)\s*\}\}/g;

function escapeHtml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

export function highlightTemplate(
  text: string,
  nodeColors: Record<string, string>
): string {
  let escaped = escapeHtml(text);
  escaped = escaped.replace(REF_RE, (full, nodeId: string, field: string) => {
    const color = nodeColors[nodeId];
    if (color) {
      return `<span style="color:${color};border-bottom:1px solid ${color}">{{${nodeId}.${field}}}</span>`;
    }
    return `<span style="color:#ef4444">{{${nodeId}.${field}}}</span>`;
  });
  return escaped;
}
