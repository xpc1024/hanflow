"use client";
import { FormRenderer } from "./FormRenderer";
import { useInspectorStore } from "@/stores/inspectorStore";
import { getSchema, FALLBACK_SCHEMAS } from "@/lib/dsl/schemaCache";
import { checkConfig, checkReferences } from "@/lib/dsl/validate";
import { getCompletionSources } from "@/lib/dsl/completion";
import { useCanvasStore } from "@/stores/canvasStore";
import type { NodeType } from "@/lib/dsl/types";

interface Props { nodeType: NodeType; nodeId: string; nodeIds: Set<string>; }

export function ConfigForm({ nodeType, nodeId, nodeIds }: Props) {
  const { draftConfig, updateDraftConfig } = useInspectorStore();
  const schema = getSchema(nodeType);
  const cfg = draftConfig ?? {};
  const valResult = checkConfig(nodeType, cfg, schema.validation_rules);

  const refErrors: Record<string, string> = {};
  for (const [field, def] of Object.entries(schema.config_schema.properties ?? {})) {
    if ((def as any).type === "string" && typeof cfg[field] === "string") {
      const rr = checkReferences(cfg[field] as string, nodeIds);
      if (!rr.valid) refErrors[field] = `Unresolved: ${rr.unresolved.join(", ")}`;
    }
  }

  const errors: Record<string, string> = {};
  for (const e of valResult.errors) if (e.field) errors[e.field] = e.message;
  Object.assign(errors, refErrors);

  const allNodes = useCanvasStore.getState().nodes;
  const allEdges = useCanvasStore.getState().edges;
  const depsByNode: Record<string, string[]> = {};
  for (const e of allEdges) (depsByNode[e.target] ??= []).push(e.source);
  const workflowNodes = allNodes.map((n) => ({ id: n.id, type: n.data.nodeType as NodeType, depends_on: depsByNode[n.id] ?? [] }));
  const nodeColors: Record<string, string> = {};
  for (const n of allNodes) nodeColors[n.id] = getSchema(n.data.nodeType as NodeType).visual.color;

  const allNodeTypes = Object.keys(FALLBACK_SCHEMAS) as NodeType[];
  const outputSchemas = Object.fromEntries(allNodeTypes.map((t) => [t, getSchema(t).output_schema])) as Record<NodeType, { fields: Record<string, string> }>;
  const completionSources = getCompletionSources(nodeId, workflowNodes, outputSchemas);

  return <FormRenderer schema={schema.config_schema} values={cfg} onChange={updateDraftConfig} errors={errors} nodeColors={nodeColors} />;
}
