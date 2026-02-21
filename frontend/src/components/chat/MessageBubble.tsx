import type { ChatMessage, DisplayData } from "../../lib/types";
import { SQLBlock } from "./SQLBlock";
import { VizRenderer } from "../viz/VizRenderer";

interface MessageBubbleProps {
  message: ChatMessage;
  onVizClick?: (display: DisplayData) => void;
}

export function MessageBubble({ message, onVizClick }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[75%] rounded-lg px-4 py-2.5 ${
          isUser
            ? "bg-blue-600 text-white dark:bg-blue-500"
            : "bg-gray-100 text-gray-900 dark:bg-gray-800 dark:text-gray-100"
        }`}
      >
        <p className="whitespace-pre-wrap text-sm leading-relaxed">
          {message.content}
          {message.isStreaming && (
            <span className="ml-0.5 inline-block h-4 w-1 animate-pulse bg-current" />
          )}
        </p>

        {!isUser && message.sql && <SQLBlock sql={message.sql} />}

        {!isUser && message.display && (
          <div
            className="mt-3 cursor-pointer rounded-lg border border-gray-200 bg-white p-3 transition-shadow hover:shadow-md dark:border-gray-600 dark:bg-gray-900"
            onClick={() => onVizClick?.(message.display!)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onVizClick?.(message.display!);
              }
            }}
            aria-label="Click to expand visualization"
          >
            <VizRenderer display={message.display} compact />
            <p className="mt-2 text-center text-[10px] text-gray-400 dark:text-gray-500">
              Click to expand
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
