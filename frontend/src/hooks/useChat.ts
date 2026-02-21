import { type Dispatch, type SetStateAction, useCallback, useRef, useState } from "react";
import { fetchEventSource } from "@microsoft/fetch-event-source";
import type { ChatMessage, DisplayData, ToolStatus } from "../lib/types";

let nextId = 0;
function genId(): string {
  return `msg-${Date.now()}-${nextId++}`;
}

interface UseChatReturn {
  messages: ChatMessage[];
  toolStatus: ToolStatus | null;
  isLoading: boolean;
  submit: (conversationId: string, content: string, options?: { hidden?: boolean }) => void;
  stop: () => void;
  setMessages: Dispatch<SetStateAction<ChatMessage[]>>;
}

export function useChat(): UseChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [toolStatus, setToolStatus] = useState<ToolStatus | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const stop = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setIsLoading(false);
    setToolStatus(null);
  }, []);

  const submit = useCallback(
    (conversationId: string, content: string, options?: { hidden?: boolean }) => {
      if (isLoading) return;

      const userMsg: ChatMessage = {
        id: genId(),
        role: "user",
        content,
        hidden: options?.hidden,
      };

      const assistantId = genId();
      const assistantMsg: ChatMessage = {
        id: assistantId,
        role: "assistant",
        content: "",
        isStreaming: true,
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setIsLoading(true);
      setToolStatus(null);

      const ctrl = new AbortController();
      abortRef.current = ctrl;

      let accumulated = "";

      fetchEventSource(`/api/conversations/${conversationId}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content }),
        credentials: "include",
        signal: ctrl.signal,

        onopen: async (response) => {
          if (!response.ok) {
            throw new Error(`SSE open failed: ${response.status}`);
          }
        },

        onmessage: (event) => {
          if (!event.data) return;

          switch (event.event) {
            case "token": {
              const { content: token } = JSON.parse(event.data) as {
                content: string;
              };
              accumulated += token;
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? { ...m, content: accumulated }
                    : m,
                ),
              );
              break;
            }
            case "tool_start": {
              const { tool } = JSON.parse(event.data) as { tool: string };
              setToolStatus({ tool, active: true });
              break;
            }
            case "tool_end": {
              setToolStatus(null);
              break;
            }
            case "message_complete": {
              const data = JSON.parse(event.data) as {
                content: string;
                sql?: string;
                display?: DisplayData;
              };
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? {
                        ...m,
                        content: data.content,
                        sql: data.sql,
                        display: data.display,
                        isStreaming: false,
                      }
                    : m,
                ),
              );
              setIsLoading(false);
              setToolStatus(null);
              break;
            }
            case "error": {
              const { error } = JSON.parse(event.data) as { error: string };
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? {
                        ...m,
                        content: `Error: ${error}`,
                        isStreaming: false,
                      }
                    : m,
                ),
              );
              setIsLoading(false);
              setToolStatus(null);
              break;
            }
          }
        },

        onerror: (err) => {
          if (ctrl.signal.aborted) return;
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? {
                    ...m,
                    content: accumulated || `Connection error: ${String(err)}`,
                    isStreaming: false,
                  }
                : m,
            ),
          );
          setIsLoading(false);
          setToolStatus(null);
          throw err; // stop retrying
        },

        onclose: () => {
          setIsLoading(false);
          setToolStatus(null);
        },
      }).catch(() => {
        // Connection-level errors are handled by onerror callback
      });
    },
    [isLoading],
  );

  return { messages, toolStatus, isLoading, submit, stop, setMessages };
}
