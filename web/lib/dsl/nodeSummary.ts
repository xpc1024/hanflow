import type { NodeType } from "./types";

export interface NodeSummary {
  lines: string[];
  status: "complete" | "incomplete" | "invalid";
}

function truncate(s: string, n: number): string {
  return s.length > n ? s.slice(0, n) + "..." : s;
}

export function getNodeSummary(
  nt: NodeType,
  config: Record<string, any>
): NodeSummary {
  switch (nt) {
    case "LLM": {
      const t = config.template || config.prompt;
      return t
        ? { lines: [truncate(String(t), 60), config.model ? `model: ${config.model}` : ""].filter(Boolean), status: "complete" }
        : { lines: ["No prompt"], status: "incomplete" };
    }
    case "Tool":
      return config.tool
        ? { lines: [String(config.tool), `${Object.keys(config.args ?? {}).length} args`], status: "complete" }
        : { lines: ["No tool"], status: "incomplete" };
    case "Research":
      return config.query
        ? { lines: [truncate(String(config.query), 60), `${config.depth ?? "standard"} | ${config.max_sources ?? 10} src`], status: "complete" }
        : { lines: ["No query"], status: "incomplete" };
    case "Execution":
      return config.task
        ? { lines: [truncate(String(config.task), 60), `${config.sandbox ?? "docker"} | ${config.max_steps ?? 20} steps`], status: "complete" }
        : { lines: ["No task"], status: "incomplete" };
    case "Coordinator":
      return { lines: [`Agents: ${(config.sub_agents ?? []).join(", ") || "none"}`, `Iter: ${config.max_iterations ?? 5} | replan: ${config.replan ? "on" : "off"}`], status: (config.sub_agents ?? []).length ? "complete" : "incomplete" };
    case "HITL":
      return { lines: [`Actions: ${(config.actions ?? ["approve", "edit", "reject", "reroute"]).join(", ")}`, config.timeout_seconds ? `Timeout: ${config.timeout_seconds}s` : ""].filter(Boolean), status: "complete" };
    case "Memory":
      return { lines: [`${config.action ?? "read"} | ${config.key ?? ""}`], status: config.action && config.key ? "complete" : "incomplete" };
    case "Subworkflow":
      return { lines: [config.ref ? `-> ${config.ref}` : "No ref"], status: config.ref ? "complete" : "incomplete" };
    case "Knowledge":
      return { lines: [`${config.store ?? "no store"} | ${truncate(String(config.query ?? ""), 40)}`], status: config.store && config.query ? "complete" : "incomplete" };
    case "Parallel":
      return { lines: [`join ${config.join ?? "all"} | ${config.n ?? ""}`.trim()], status: "complete" };
    case "Loop":
      return { lines: [`${config.max_iterations ?? 100}x iterations`], status: "complete" };
    case "Branch":
      return { lines: [`${Object.keys(config.cases ?? {}).length} cases${config.default ? " + default" : ""}`], status: "complete" };
    case "Sequential":
    default:
      return { lines: ["Sequential"], status: "complete" };
  }
}
