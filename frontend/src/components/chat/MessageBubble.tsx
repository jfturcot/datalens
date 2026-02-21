import ReactMarkdown from "react-markdown";
import type { ChatMessage, DisplayData } from "../../lib/types";
import { StreamingStatus } from "./StreamingStatus";
import { VizRenderer } from "../viz/VizRenderer";

interface MessageBubbleProps {
  message: ChatMessage;
  onVizClick?: (display: DisplayData, sql?: string) => void;
  onStop?: () => void;
}

const DISPLAY_TYPE_RE =
  /"type"\s*:\s*"(?:text|table|bar_chart|line_chart|pie_chart|scatter_plot)"/;

/**
 * Strip display-hint JSON from content so raw JSON doesn't flash in the
 * bubble while streaming.  Handles both fenced (```json … ```) and bare
 * JSON blocks the LLM may produce.
 */
function stripDisplayHints(text: string): string {
  // Remove complete fenced blocks: ```...```
  let result = text.replace(/```[\s\S]*?```/g, "");
  // Remove any trailing unclosed fence (still streaming)
  result = result.replace(/```[\s\S]*$/, "");

  // Remove bare JSON visualization blocks (complete or still streaming).
  // Walk backwards to find the last '{' that looks like a display hint.
  const partialStartRe = /^\{\s*"(?:type|display)"\s*:/;
  for (let i = result.length - 1; i >= 0; i--) {
    if (result[i] === "{") {
      const rest = result.substring(i);
      if (DISPLAY_TYPE_RE.test(rest) || partialStartRe.test(rest)) {
        result = result.substring(0, i);
        break;
      }
    }
  }

  return result.trim();
}

export function MessageBubble({ message, onVizClick, onStop }: MessageBubbleProps) {
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
        <div className="text-sm leading-relaxed">
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <ReactMarkdown
              components={{
                p: ({ children }) => (
                  <p className="mb-2 last:mb-0 whitespace-pre-wrap">{children}</p>
                ),
                strong: ({ children }) => (
                  <strong className="font-semibold">{children}</strong>
                ),
                em: ({ children }) => <em className="italic">{children}</em>,
                ul: ({ children }) => (
                  <ul className="mb-2 ml-4 list-disc space-y-1">{children}</ul>
                ),
                ol: ({ children }) => (
                  <ol className="mb-2 ml-4 list-decimal space-y-1">{children}</ol>
                ),
                li: ({ children }) => <li>{children}</li>,
                code: ({ className, children }) => {
                  const isBlock = className?.includes("language-");
                  return isBlock ? (
                    <code className={className}>{children}</code>
                  ) : (
                    <code className="rounded bg-gray-200 px-1 py-0.5 text-xs dark:bg-gray-700">
                      {children}
                    </code>
                  );
                },
                pre: ({ children }) => (
                  <pre className="mb-2 overflow-x-auto rounded bg-gray-200 p-2 text-xs dark:bg-gray-700">
                    {children}
                  </pre>
                ),
                h1: ({ children }) => (
                  <h1 className="mb-2 mt-3 text-lg font-bold">{children}</h1>
                ),
                h2: ({ children }) => (
                  <h2 className="mb-1 mt-2 text-base font-bold">{children}</h2>
                ),
                h3: ({ children }) => (
                  <h3 className="mb-1 mt-2 font-semibold">{children}</h3>
                ),
              }}
            >
              {stripDisplayHints(message.content)}
            </ReactMarkdown>
          )}
          {message.isStreaming && (
            <StreamingStatus
              hasVisibleContent={!!stripDisplayHints(message.content)}
              hasCodeFence={
                message.content.includes("```") ||
                DISPLAY_TYPE_RE.test(message.content) ||
                /\{\s*"(?:type|display)"\s*:/.test(message.content)
              }
              onStop={onStop}
            />
          )}
        </div>

        {!isUser && message.display && (
          <div
            className="mt-3 cursor-pointer rounded-lg border border-gray-200 bg-white p-3 transition-shadow hover:shadow-md dark:border-gray-600 dark:bg-gray-900"
            onClick={() => onVizClick?.(message.display!, message.sql)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onVizClick?.(message.display!, message.sql);
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
