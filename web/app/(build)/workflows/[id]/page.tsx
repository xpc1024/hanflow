"use client";
import { useEffect } from "react";
import { useParams } from "next/navigation";
import { StudioShell } from "@/components/canvas/StudioShell";
import { useWorkflowStore } from "@/stores/workflowStore";

export default function WorkflowPage() {
  const params = useParams();
  const id = params.id as string;
  const { openWorkflow, current } = useWorkflowStore();

  useEffect(() => {
    if (id && (!current || current.id !== id)) openWorkflow(id);
  }, [id]);

  if (!current || current.id !== id) return <div style={{ padding: 24, color: "var(--text-secondary)" }}>Loading...</div>;
  return <StudioShell />;
}
