import { useEffect, useRef } from "react";
import type { ChatMessage, DisplayData, ToolStatus } from "../../lib/types";
import { ChatInput } from "./ChatInput";
import { MessageBubble } from "./MessageBubble";
import { StatusIndicator } from "./StatusIndicator";
import { SuggestionChips } from "./SuggestionChips";

interface ChatWindowProps {
  messages: ChatMessage[];
  toolStatus: ToolStatus | null;
  isLoading: boolean;
  inputDisabled: boolean;
  onSubmit: (content: string) => void;
  onStop: () => void;
  onVizClick?: (display: DisplayData, sql?: string) => void;
  showSuggestions?: boolean;
}

export function ChatWindow({
  messages,
  toolStatus,
  isLoading,
  inputDisabled,
  onSubmit,
  onStop,
  onVizClick,
  showSuggestions,
}: ChatWindowProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, toolStatus]);

  const visibleMessages = messages.filter((m) => !m.hidden);

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-3xl space-y-4 p-4">
          {visibleMessages.length === 0 && !inputDisabled && (
            <div className="flex items-center justify-center py-16">
              <p className="text-sm text-gray-400 dark:text-gray-500">
                Ask a question about your data
              </p>
            </div>
          )}
          {visibleMessages.map((msg) => (
            <MessageBubble
              key={msg.id}
              message={msg}
              onVizClick={onVizClick}
              onStop={msg.isStreaming ? onStop : undefined}
            />
          ))}
          {toolStatus && <StatusIndicator status={toolStatus} />}
          <div ref={bottomRef} />
        </div>
      </div>
      {showSuggestions && <SuggestionChips onSelect={onSubmit} />}
      <ChatInput
        disabled={inputDisabled || isLoading}
        onSubmit={onSubmit}
        isLoading={isLoading}
        onStop={onStop}
      />
    </div>
  );
}
