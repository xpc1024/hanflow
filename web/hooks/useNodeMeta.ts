"use client";
import { useEffect, useState } from "react";
import { FALLBACK_NODE_META, mergeMeta, type NodeMeta } from "@/lib/dsl/nodeMeta";
import { apiFetch } from "@/lib/api/client";
import type { NodeType } from "@/lib/dsl/types";

export function useNodeMeta() {
  const [meta, setMeta] = useState<Record<NodeType, NodeMeta>>(FALLBACK_NODE_META);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const results = await Promise.all(
          (Object.keys(FALLBACK_NODE_META) as NodeType[]).map(async (t) => {
            const r = await apiFetch<{ visual: NodeMeta }>(`/api/schema/node/${t}`);
            return [t, r.visual] as const;
          })
        );
        if (!cancelled) {
          setMeta(
            mergeMeta(
              Object.fromEntries(results) as Partial<Record<NodeType, NodeMeta>>
            )
          );
        }
      } catch {
        // Keep fallback on failure
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return meta;
}
