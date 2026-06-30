import { WorkflowCanvas } from "@/components/canvas/WorkflowCanvas";
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
    <main style={{ padding: 24 }}>
      <h1>Hanflow Studio</h1>
      <WorkflowCanvas dsl={sampleDsl} />
    </main>
  );
}
