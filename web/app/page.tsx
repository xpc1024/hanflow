import { BuildMode } from "@/components/canvas/BuildMode";
import type { WorkflowDSL } from "@/lib/dsl/types";

const sampleDsl: WorkflowDSL = {
  name: "demo",
  nodes: [
    { id: "intake", type: "LLM", config: { template: "parse request" } },
    {
      id: "research",
      type: "Coordinator",
      depends_on: ["intake"],
      config: { sub_agents: ["researcher"] },
    },
    { id: "report", type: "Execution", depends_on: ["research"] },
  ],
};

export default function Home() {
  return (
    <main style={{ padding: 16, height: "100vh", display: "flex", flexDirection: "column" }}>
      <h1 style={{ margin: "0 0 12px", fontSize: 20 }}>Hanflow Studio — Build</h1>
      <div style={{ flex: 1 }}>
        <BuildMode initialDsl={sampleDsl} />
      </div>
    </main>
  );
}
