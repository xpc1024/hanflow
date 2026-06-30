"use client";

import { useState } from "react";
import { BuildMode } from "@/components/canvas/BuildMode";
import { MonitorView } from "@/components/monitor/MonitorView";
import { HitlPanel } from "@/components/hitl/HitlPanel";
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
  const [tab, setTab] = useState<"build" | "monitor" | "hitl">("build");

  return (
    <main style={{ padding: 16, height: "100vh", display: "flex", flexDirection: "column" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 12 }}>
        <h1 style={{ margin: 0, fontSize: 20 }}>Hanflow Studio</h1>
        <div style={{ display: "flex", gap: 4 }}>
          {(["build", "monitor", "hitl"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              style={{
                padding: "6px 16px",
                border: "1px solid #d1d5db",
                borderBottom: tab === t ? "2px solid #3b82f6" : "1px solid #d1d5db",
                borderRadius: "6px 6px 0 0",
                background: tab === t ? "#eff6ff" : "#fff",
                cursor: "pointer",
                fontSize: 13,
                fontWeight: tab === t ? 600 : 400,
                color: tab === t ? "#3b82f6" : "#6b7280",
              }}
            >
              {t === "build" ? "Build" : "Monitor"}
            </button>
          ))}
        </div>
      </div>
      <div style={{ flex: 1, border: "1px solid #e5e7eb", borderRadius: 8, overflow: "hidden" }}>
        {tab === "build" ? <BuildMode initialDsl={sampleDsl} /> : tab === "monitor" ? <MonitorView /> : <HitlPanel />}
      </div>
    </main>
  );
}
