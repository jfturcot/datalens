import type { DisplayData } from "./types";

const DISPLAY_TYPES = new Set([
  "text",
  "table",
  "bar_chart",
  "line_chart",
  "pie_chart",
  "scatter_plot",
]);

/**
 * Find a brace-balanced JSON substring starting at `text[start]`.
 * Returns the substring or null if braces never balance.
 */
function findBraceBalancedJson(text: string, start: number): string | null {
  if (start >= text.length || text[start] !== "{") return null;
  let depth = 0;
  let inString = false;
  let escape = false;
  for (let i = start; i < text.length; i++) {
    const ch = text[i];
    if (escape) {
      escape = false;
      continue;
    }
    if (ch === "\\") {
      if (inString) escape = true;
      continue;
    }
    if (ch === '"') {
      inString = !inString;
      continue;
    }
    if (inString) continue;
    if (ch === "{") depth++;
    else if (ch === "}") {
      depth--;
      if (depth === 0) return text.slice(start, i + 1);
    }
  }
  return null;
}

/**
 * Client-side fallback: extract a display-hint JSON from message content.
 * Returns `{ display, cleanedContent }` where cleanedContent has the JSON
 * block stripped out.
 */
export function extractDisplay(content: string): {
  display: DisplayData | null;
  cleanedContent: string;
} {
  // Strategy 1: fenced code block ```json { ... } ```
  const fenceRe = /```(?:json)?\s*\{/gs;
  let m: RegExpExecArray | null;
  while ((m = fenceRe.exec(content)) !== null) {
    const braceStart = m.index + m[0].length - 1;
    const blob = findBraceBalancedJson(content, braceStart);
    if (!blob) continue;
    try {
      const parsed: unknown = JSON.parse(blob);
      if (
        parsed &&
        typeof parsed === "object" &&
        "type" in parsed &&
        DISPLAY_TYPES.has((parsed as Record<string, unknown>).type as string)
      ) {
        const blockEnd = content.indexOf("```", braceStart + blob.length);
        const fenceEnd = blockEnd !== -1 ? blockEnd + 3 : braceStart + blob.length;
        const cleaned = (content.slice(0, m.index) + content.slice(fenceEnd)).trim();
        return { display: parsed as DisplayData, cleanedContent: cleaned };
      }
    } catch {
      continue;
    }
  }

  // Strategy 2: bare JSON object with a display type key
  for (let i = 0; i < content.length; i++) {
    if (content[i] !== "{") continue;
    const blob = findBraceBalancedJson(content, i);
    if (!blob) continue;
    try {
      const parsed: unknown = JSON.parse(blob);
      if (
        parsed &&
        typeof parsed === "object" &&
        "type" in parsed &&
        DISPLAY_TYPES.has((parsed as Record<string, unknown>).type as string)
      ) {
        const cleaned = (content.slice(0, i) + content.slice(i + blob.length)).trim();
        return { display: parsed as DisplayData, cleanedContent: cleaned };
      }
    } catch {
      continue;
    }
  }

  return { display: null, cleanedContent: content };
}
