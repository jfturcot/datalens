import { useCallback, useState } from "react";

interface SQLBlockProps {
  sql: string;
}

export function SQLBlock({ sql }: SQLBlockProps) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const copy = useCallback(async () => {
    await navigator.clipboard.writeText(sql);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }, [sql]);

  return (
    <div className="mt-2 rounded-md border border-gray-200 dark:border-gray-700">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center gap-2 px-3 py-1.5 text-xs font-medium text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
      >
        <svg
          className={`h-3 w-3 transition-transform ${open ? "rotate-90" : ""}`}
          fill="currentColor"
          viewBox="0 0 20 20"
        >
          <path
            fillRule="evenodd"
            d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z"
            clipRule="evenodd"
          />
        </svg>
        SQL Query
      </button>
      {open && (
        <div className="relative border-t border-gray-200 dark:border-gray-700">
          <pre className="overflow-x-auto bg-gray-50 p-3 text-xs text-gray-800 dark:bg-gray-800/50 dark:text-gray-200">
            <code>{sql}</code>
          </pre>
          <button
            onClick={copy}
            className="absolute right-2 top-2 rounded px-2 py-0.5 text-xs text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300"
          >
            {copied ? "Copied!" : "Copy"}
          </button>
        </div>
      )}
    </div>
  );
}
