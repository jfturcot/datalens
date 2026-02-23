import type { DisplayData } from "../../lib/types";

interface TextAnswerProps {
  display: DisplayData;
}

export function TextAnswer({ display }: TextAnswerProps) {
  const row = (display.data ?? [])[0];
  if (!row) return null;

  const entries = Object.entries(row);
  const firstEntry = entries[0];
  if (!firstEntry) return null;

  const value = String(firstEntry[1]);
  const label = display.title ?? firstEntry[0];

  return (
    <div className="flex flex-col items-center gap-1 rounded-lg bg-white/60 p-4 dark:bg-gray-700/40">
      <span className="text-2xl font-bold text-blue-600 dark:text-blue-400">
        {value}
      </span>
      {label && (
        <span className="text-xs text-gray-500 dark:text-gray-400">
          {label}
        </span>
      )}
    </div>
  );
}
