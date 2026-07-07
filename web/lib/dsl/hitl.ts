const PRIMARY_FIELD_MAP: Record<string, string> = {
  LLM: "content", Tool: "result", Research: "summary",
  Coordinator: "result", Memory: "value",
};

export function getPrimaryField(
  nodeType: string,
  currentValue: Record<string, any>,
  config: Record<string, any> = {}
): { field: string; value: string; editable: boolean; isJson: boolean } {
  if (config.editable_field) {
    return { field: config.editable_field, value: String(currentValue[config.editable_field] ?? ""), editable: true, isJson: false };
  }
  const mapped = PRIMARY_FIELD_MAP[nodeType];
  if (mapped && currentValue[mapped] !== undefined) {
    return { field: mapped, value: String(currentValue[mapped]), editable: true, isJson: false };
  }
  if (["Execution", "Subworkflow", "Sequential", "Parallel", "Loop", "Branch", "Knowledge"].includes(nodeType)) {
    return { field: "", value: "", editable: false, isJson: false };
  }
  return { field: "", value: JSON.stringify(currentValue, null, 2), editable: true, isJson: true };
}

export interface ApprovalInput {
  action: "approve" | "edit" | "reject" | "reroute";
  currentValue: Record<string, any>;
  primaryField: string;
  primaryValue: string;
  formValues: Record<string, any>;
  reason?: string;
  rerouteTarget?: string;
}

export interface ApprovalPayload {
  action: string;
  edited_value?: Record<string, any>;
  reason?: string;
  reroute_target?: string;
  form: Record<string, any>;
  decided_by?: string;
}

export function buildApprovalPayload(input: ApprovalInput): ApprovalPayload {
  const { action, currentValue, primaryField, primaryValue, formValues } = input;
  if (action === "reject" && !input.reason) throw new Error("Reason is required for reject");
  if (action === "reroute" && (!input.rerouteTarget || !input.reason)) throw new Error("Reroute target and reason are required");

  const payload: ApprovalPayload = { action, form: formValues, decided_by: "anonymous" };

  if (action === "edit") {
    if (typeof currentValue === "object" && currentValue !== null && !Array.isArray(currentValue)) {
      payload.edited_value = { ...currentValue, [primaryField]: primaryValue };
    } else {
      payload.edited_value = { [primaryField]: primaryValue };
    }
  }
  if (action === "reject") payload.reason = input.reason;
  if (action === "reroute") { payload.reroute_target = input.rerouteTarget; payload.reason = input.reason; }
  return payload;
}
