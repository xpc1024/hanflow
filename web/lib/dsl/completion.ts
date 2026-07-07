import type { NodeType, WorkflowNode } from "./types";

export function transitiveDeps(nodeId: string, nodes: WorkflowNode[]): string[] {
  const byId = new Map(nodes.map((n) => [n.id, n]));
  const seen = new Set<string>();
  const stack = [...(byId.get(nodeId)?.depends_on ?? [])];
  while (stack.length) {
    const d = stack.pop()!;
    if (seen.has(d)) continue;
    seen.add(d);
    stack.push(...(byId.get(d)?.depends_on ?? []));
  }
  return Array.from(seen);
}

export interface CompletionSource {
  nodeId: string;
  nodeType: NodeType;
  fields: { name: string; type: string }[];
}

export function getCompletionSources(
  currentNodeId: string,
  nodes: WorkflowNode[],
  outputSchemas: Record<NodeType, { fields: Record<string, string> }>
): CompletionSource[] {
  const byId = new Map(nodes.map((n) => [n.id, n]));
  return transitiveDeps(currentNodeId, nodes).map((id) => {
    const n = byId.get(id)!;
    const fields = outputSchemas[n.type]?.fields ?? {};
    return {
      nodeId: id,
      nodeType: n.type,
      fields: Object.entries(fields).map(([name, type]) => ({ name, type })),
    };
  });
}
