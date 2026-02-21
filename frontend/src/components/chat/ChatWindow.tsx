import { useEffect, useRef } from "react";
import type { ChatMessage, DisplayData, ToolStatus } from "../../lib/types";
import { ChatInput } from "./ChatInput";
import { MessageBubble } from "./MessageBubble";
import { StatusIndicator } from "./StatusIndicator";

interface ChatWindowProps {
  messages: ChatMessage[];
  toolStatus: ToolStatus | null;
  isLoading: boolean;
  inputDisabled: boolean;
  onSubmit: (content: string) => void;
  onStop: () => void;
  onVizClick?: (display: DisplayData) => void;
}

export function ChatWindow({
  messages,
  toolStatus,
  isLoading,
  inputDisabled,
  onSubmit,
  onStop,
  onVizClick,
}: ChatWindowProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, toolStatus]);

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-3xl space-y-4 p-4">
          {messages.length === 0 && !inputDisabled && (
            <div className="flex items-center justify-center py-16">
              <p className="text-sm text-gray-400 dark:text-gray-500">
                Ask a question about your data
              </p>
            </div>
          )}
          {messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} onVizClick={onVizClick} />
          ))}
          {toolStatus && <StatusIndicator status={toolStatus} />}
          <div ref={bottomRef} />
        </div>
      </div>
      <ChatInput
        disabled={inputDisabled || isLoading}
        onSubmit={onSubmit}
        isLoading={isLoading}
        onStop={onStop}
      />
    </div>
  );
}
