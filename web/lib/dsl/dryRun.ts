export function formatDryRunOutput(nodeType: string, output: Record<string, any>): { summary: string; full: unknown } {
  const mainField: Record<string, string> = {
    LLM: "content", Tool: "result", Research: "summary",
    Execution: "output", Coordinator: "result", Memory: "value",
  };
  const mf = mainField[nodeType];
  let summary = "";
  if (mf && output[mf] !== undefined) summary = String(output[mf]);
  else summary = JSON.stringify(output).slice(0, 100);
  summary = summary.length > 30 ? summary.slice(0, 30) + "..." : summary;
  return { summary, full: output };
}
