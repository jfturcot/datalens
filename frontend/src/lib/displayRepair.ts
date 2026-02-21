import type { DisplayData } from "./types";

/**
 * Validate and auto-repair display data so axis/key fields reference
 * actual column names in the data array. The LLM sometimes uses display
 * labels ("Industry") instead of column keys ("industry_vertical").
 */
export function repairDisplay(display: DisplayData): DisplayData {
  if (!display.data || display.data.length === 0) return display;

  const first = display.data[0];
  if (!first) return display;
  const keys = Object.keys(first);
  if (keys.length === 0) return display;

  const repaired = { ...display };

  if (display.type === "pie_chart") {
    repaired.label_key = resolveKey(display.label_key, keys, "string");
    repaired.value_key = resolveKey(display.value_key, keys, "number");
  } else if (
    display.type === "bar_chart" ||
    display.type === "line_chart" ||
    display.type === "scatter_plot"
  ) {
    repaired.x_axis = resolveKey(display.x_axis, keys, "string");
    repaired.y_axis = resolveKey(display.y_axis, keys, "number");
  }

  return repaired;
}

/**
 * Resolve a key reference against actual data keys.
 * 1. Exact match → use it
 * 2. Case-insensitive match → use the real key
 * 3. Infer by type preference (string col for labels, number col for values)
 */
function resolveKey(
  given: string | undefined,
  keys: string[],
  _preferType: "string" | "number",
): string | undefined {
  if (!given) return given;

  // 1. Exact match
  if (keys.includes(given)) return given;

  // 2. Case-insensitive match
  const lower = given.toLowerCase();
  const ciMatch = keys.find((k) => k.toLowerCase() === lower);
  if (ciMatch) return ciMatch;

  // 3. Fuzzy: check if any key contains the given string or vice-versa
  const fuzzy = keys.find(
    (k) =>
      k.toLowerCase().includes(lower) ||
      lower.includes(k.toLowerCase()),
  );
  if (fuzzy) return fuzzy;

  // 4. Give up on matching the given name — infer from data types
  return undefined;
}
