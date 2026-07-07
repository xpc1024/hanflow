import { describe, it, expect } from "vitest";
import { getSchema, mergeSchema, FALLBACK_SCHEMAS } from "@/lib/dsl/schemaCache";
import type { NodeType } from "@/lib/dsl/types";

describe("schemaCache", () => {
  it("fallback has all 13 types", () => {
    expect(Object.keys(FALLBACK_SCHEMAS)).toHaveLength(13);
  });
  it("getSchema returns fallback by default", () => {
    const s = getSchema("LLM" as NodeType);
    expect(s.config_schema.properties.template).toBeTruthy();
  });
  it("mergeSchema prefers server", () => {
    mergeSchema({
      LLM: {
        config_schema: { type: "object", properties: { template: { type: "string", format: "textarea" } } },
        validation_rules: { alternatives: [["template", "prompt"]] },
        output_schema: { fields: {} },
        default_config: {},
        visual: { color: "#server", group: "leaf" },
      },
    } as any);
    expect(getSchema("LLM" as NodeType).visual.color).toBe("#server");
    expect(getSchema("HITL" as NodeType).visual.color).toBe(FALLBACK_SCHEMAS.HITL.visual.color);
  });
});
