import type { ConversationResponse } from "../../lib/types";

interface SidebarProps {
  conversations: ConversationResponse[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
}

export function Sidebar({
  conversations,
  activeId,
  onSelect,
  onNew,
  onDelete,
}: SidebarProps) {
  return (
    <aside className="flex h-full w-64 flex-col border-r border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-800">
      <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3 dark:border-gray-700">
        <span className="text-sm font-medium text-gray-600 dark:text-gray-300">
          Conversations
        </span>
        <button
          onClick={onNew}
          className="rounded p-1 text-gray-500 hover:bg-gray-200 dark:text-gray-400 dark:hover:bg-gray-700"
          aria-label="New conversation"
        >
          <svg
            className="h-4 w-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 4v16m8-8H4"
            />
          </svg>
        </button>
      </div>
      <nav className="flex-1 overflow-y-auto p-2">
        {conversations.length === 0 && (
          <p className="px-2 py-4 text-center text-xs text-gray-400 dark:text-gray-500">
            Upload a CSV to start
          </p>
        )}
        {conversations.map((c) => (
          <div
            key={c.id}
            className={`group mb-1 flex items-center justify-between rounded-md px-3 py-2 text-sm cursor-pointer ${
              c.id === activeId
                ? "bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-200"
                : "text-gray-700 hover:bg-gray-200 dark:text-gray-300 dark:hover:bg-gray-700"
            }`}
            onClick={() => onSelect(c.id)}
          >
            <span className="truncate">{c.filename}</span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete(c.id);
              }}
              className="ml-2 hidden rounded p-0.5 text-gray-400 hover:text-red-500 group-hover:block dark:text-gray-500 dark:hover:text-red-400"
              aria-label={`Delete ${c.filename}`}
            >
              <svg
                className="h-3.5 w-3.5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>
        ))}
      </nav>
    </aside>
  );
}
