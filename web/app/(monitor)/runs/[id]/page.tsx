"use client";
import { MonitorShell } from "@/components/monitor/MonitorShell";
import { useWorkflowStore } from "@/stores/workflowStore";
import { useEffect } from "react";

export default function RunPage({ params }: { params: { id: string } }) {
  const { current: wf, openWorkflow } = useWorkflowStore();
  const runId = params.id;

  // Load the workflow that this run belongs to (so canvas has nodes)
  useEffect(() => {
    // v1: load the default workflow or the one from run info
    const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    fetch(`${API}/api/runs/${runId}`)
      .then((r) => r.json())
      .then(async (info) => {
        const wfName = info.workflow_name;
        if (wfName) await openWorkflow(wfName);
      })
      .catch(() => {});
  }, [runId]);

  return <MonitorShell runId={runId} />;
}
