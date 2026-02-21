import type { ChatMessage } from "../../lib/types";
import { SQLBlock } from "./SQLBlock";

interface MessageBubbleProps {
  message: ChatMessage;
}

export function MessageBubble({ message }: MessageBubbleProps) {
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
      </div>
    </div>
  );
}
