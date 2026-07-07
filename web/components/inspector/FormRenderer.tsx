"use client";
import { StringField } from "./fields/StringField";
import { NumberField } from "./fields/NumberField";
import { BooleanField } from "./fields/BooleanField";
import { EnumField } from "./fields/EnumField";
import { ArrayField } from "./fields/ArrayField";
import { ObjectField } from "./fields/ObjectField";
import { TemplateField } from "./fields/TemplateField";

interface Props {
  schema: { type: string; properties: Record<string, any> };
  values: Record<string, any>;
  onChange: (field: string, value: any) => void;
  errors?: Record<string, string>;
  nodeColors?: Record<string, string>;
}

const TEMPLATE_FIELDS = ["template", "prompt", "query", "task", "condition", "success_criteria"];

export function FormRenderer({ schema, values, onChange, errors = {}, nodeColors = {} }: Props) {
  const entries = Object.entries(schema.properties ?? {});
  return (
    <div>
      {entries.map(([field, def]) => {
        const val = values[field];
        const err = errors[field];
        const key = `${field}-${def.type}-${def.format ?? ""}`;
        if (def.enum) return <EnumField key={key} name={field} value={val ?? def.enum[0]} onChange={(v) => onChange(field, v)} schema={def} />;
        if (def.type === "boolean") return <BooleanField key={key} name={field} value={val ?? false} onChange={(v) => onChange(field, v)} />;
        if (def.type === "integer" || def.type === "number") return <NumberField key={key} name={field} value={val ?? 0} onChange={(v) => onChange(field, v)} schema={def} error={err} />;
        if (def.type === "array") return <ArrayField key={key} name={field} value={val ?? []} onChange={(v) => onChange(field, v)} items={def.items} />;
        if (def.type === "object") return <ObjectField key={key} name={field} value={val ?? {}} onChange={(v) => onChange(field, v)} />;
        if (def.format === "textarea" && TEMPLATE_FIELDS.includes(field))
          return <TemplateField key={key} name={field} value={val ?? ""} onChange={(v) => onChange(field, v)} nodeColors={nodeColors} />;
        return <StringField key={key} name={field} value={val ?? ""} onChange={(v) => onChange(field, v)} schema={def} error={err} />;
      })}
    </div>
  );
}
