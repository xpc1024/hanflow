export function remapIds(
  ids: string[],
  existing: Set<string>
): { mapping: Record<string, string> } {
  const mapping: Record<string, string> = {};
  for (const id of ids) {
    if (!existing.has(id)) {
      mapping[id] = id;
      continue;
    }
    let i = 1;
    while (existing.has(`${id}_copy${i}`)) i++;
    mapping[id] = `${id}_copy${i}`;
  }
  return { mapping };
}
