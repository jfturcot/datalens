import { useEffect, useState } from "react";

interface StreamingStatusProps {
  hasVisibleContent: boolean;
  hasCodeFence: boolean;
  onStop?: () => void;
}

const PROGRESS_MESSAGES = [
  { after: 0, text: "Building visualization..." },
  { after: 8, text: "Processing data..." },
  { after: 20, text: "Almost there, assembling chart..." },
  { after: 40, text: "Handling a large dataset, still working..." },
];

function formatElapsed(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}m ${s}s`;
}

export function StreamingStatus({
  hasVisibleContent,
  hasCodeFence,
  onStop,
}: StreamingStatusProps) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const id = setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => clearInterval(id);
  }, []);

  // Reset when code fence phase starts
  useEffect(() => {
    if (hasCodeFence) setElapsed(0);
  }, [hasCodeFence]);

  const cancelButton = onStop && elapsed >= 5 && (
    <button
      type="button"
      onClick={onStop}
      className="text-xs text-gray-400 underline transition-colors hover:text-red-500 dark:text-gray-500 dark:hover:text-red-400"
    >
      Cancel
    </button>
  );

  // State 1: No content yet — bouncing dots
  if (!hasVisibleContent) {
    return (
      <span className="inline-flex items-center gap-1 py-1">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="inline-block h-2 w-2 rounded-full bg-gray-400 dark:bg-gray-500"
            style={{
              animation: "bounce-dot 1.2s ease-in-out infinite",
              animationDelay: `${i * 0.2}s`,
            }}
          />
        ))}
      </span>
    );
  }

  // State 2: Content + code fence streaming — show progress
  if (hasCodeFence) {
    const message =
      [...PROGRESS_MESSAGES].reverse().find((m) => elapsed >= m.after)?.text ??
      PROGRESS_MESSAGES[0].text;

    return (
      <>
        <span className="ml-0.5 inline-block h-4 w-0.5 animate-blink bg-current" />
        <div className="mt-2 flex items-center gap-2 text-xs text-gray-400 dark:text-gray-500">
          <svg
            className="h-3 w-3 animate-spin"
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
          <span>{message}</span>
          <span className="tabular-nums">{formatElapsed(elapsed)}</span>
          {cancelButton}
        </div>
      </>
    );
  }

  // State 3: Content streaming, no code fence — blinking cursor
  return (
    <span className="ml-0.5 inline-block h-4 w-0.5 animate-blink bg-current" />
  );
}
