import type { ToolStatus } from "../../lib/types";

interface StatusIndicatorProps {
  status: ToolStatus;
}

const TOOL_LABELS: Record<string, string> = {
  inspect_schema: "Inspecting schema...",
  execute_query: "Running query...",
};

export function StatusIndicator({ status }: StatusIndicatorProps) {
  const label = TOOL_LABELS[status.tool] ?? `Running ${status.tool}...`;

  return (
    <div className="flex items-center gap-2 px-4 py-2">
      <svg
        className="h-4 w-4 animate-spin text-blue-500"
        fill="none"
        viewBox="0 0 24 24"
      >
        <circle
          className="opacity-25"
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          strokeWidth="4"
        />
        <path
          className="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
        />
      </svg>
      <span className="text-sm text-gray-500 dark:text-gray-400">{label}</span>
    </div>
  );
}
