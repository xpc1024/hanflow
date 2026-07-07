import yaml from "yaml";
import type { WorkflowDSL } from "./types";

export function toYaml(dsl: WorkflowDSL): string {
  return yaml.stringify({ workflow: dsl });
}

export function fromYaml(text: string): WorkflowDSL {
  const data = yaml.parse(text);
  if (data?.workflow) return data.workflow;
  return data;
}
