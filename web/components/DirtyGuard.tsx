"use client";
import { useEffect } from "react";
import { useWorkflowStore } from "@/stores/workflowStore";

export function DirtyGuard() {
  const dirty = useWorkflowStore((s) => s.current?.dirty ?? false);
  useEffect(() => {
    const handler = (e: BeforeUnloadEvent) => {
      if (dirty) { e.preventDefault(); e.returnValue = ""; }
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [dirty]);
  return null;
}
