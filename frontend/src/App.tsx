import { useCallback, useEffect, useRef, useState } from "react";
import { Layout } from "./components/layout/Layout";
import { FileDropZone } from "./components/chat/FileDropZone";
import { ChatWindow } from "./components/chat/ChatWindow";
import { VizPanel } from "./components/viz/VizPanel";
import { createSession, getMySession } from "./lib/api";
import { useChat } from "./hooks/useChat";
import { useFileUpload } from "./hooks/useFileUpload";
import { useConversations } from "./hooks/useConversations";
import type { DisplayData } from "./lib/types";

type AppState = "loading" | "no-file" | "chat";

const AUTO_GREETING_PROMPT =
  "Describe this dataset briefly: what it contains, key columns, and suggest a few questions I could ask.";

function App() {
  const [appState, setAppState] = useState<AppState>("loading");
  const [sessionReady, setSessionReady] = useState(false);
  const [showDropZone, setShowDropZone] = useState(false);
  const [vizDisplay, setVizDisplay] = useState<DisplayData | null>(null);
  const [vizSql, setVizSql] = useState<string | null>(null);
  const initRef = useRef(false);
  const skipHistoryRef = useRef(false);

  const { messages, toolStatus, isLoading, submit, stop, setMessages } =
    useChat();
  const { uploading, progress, error: uploadError, upload } = useFileUpload();
  const {
    conversations,
    activeId,
    setActiveId,
    refresh,
    loadHistory,
    remove,
  } = useConversations();

  // Session initialization
  useEffect(() => {
    if (initRef.current) return;
    initRef.current = true;

    (async () => {
      try {
        await getMySession();
      } catch {
        await createSession();
      }
      setSessionReady(true);
      await refresh();
    })();
  }, [refresh]);

  // After session ready and conversations loaded, determine initial state
  useEffect(() => {
    if (!sessionReady) return;
    const first = conversations[0];
    if (first && !activeId) {
      setActiveId(first.id);
      setAppState("chat");
    } else if (conversations.length === 0 && !activeId) {
      setAppState("no-file");
    }
  }, [sessionReady, conversations, activeId, setActiveId]);

  // Load history when active conversation changes
  useEffect(() => {
    if (!activeId) return;
    if (skipHistoryRef.current) {
      skipHistoryRef.current = false;
      return;
    }
    (async () => {
      const history = await loadHistory(activeId);
      setMessages(history);
      setAppState("chat");
    })();
  }, [activeId, loadHistory, setMessages]);

  // Close viz panel when switching conversations
  useEffect(() => {
    setVizDisplay(null);
  }, [activeId]);

  const handleFile = useCallback(
    async (file: File) => {
      const result = await upload(file);
      await refresh();
      skipHistoryRef.current = true;
      setActiveId(result.conversation_id);
      setShowDropZone(false);
      setMessages([]);
      setAppState("chat");

      // Auto-trigger LLM greeting (hidden user message so only the response shows)
      submit(result.conversation_id, AUTO_GREETING_PROMPT, { hidden: true });
    },
    [upload, refresh, setActiveId, setMessages, submit],
  );

  const handleNewConversation = useCallback(() => {
    setShowDropZone(true);
    setActiveId(null);
    setMessages([]);
    setVizDisplay(null);
  }, [setActiveId, setMessages]);

  const handleSelectConversation = useCallback(
    (id: string) => {
      setShowDropZone(false);
      setActiveId(id);
    },
    [setActiveId],
  );

  const handleDelete = useCallback(
    async (id: string) => {
      await remove(id);
      if (conversations.length <= 1) {
        setAppState("no-file");
        setMessages([]);
        setVizDisplay(null);
      }
    },
    [remove, conversations.length, setMessages],
  );

  const handleSubmit = useCallback(
    (content: string) => {
      if (!activeId) return;
      submit(activeId, content);
    },
    [activeId, submit],
  );

  const handleVizClick = useCallback((display: DisplayData, sql?: string) => {
    setVizDisplay(display);
    setVizSql(sql ?? null);
  }, []);

  const handleVizClose = useCallback(() => {
    setVizDisplay(null);
    setVizSql(null);
  }, []);

  const hasUserMessage = messages.some(
    (m) => m.role === "user" && !m.hidden,
  );
  const showSuggestions =
    appState === "chat" && !!activeId && !hasUserMessage && !isLoading;

  if (appState === "loading") {
    return (
      <div className="flex h-screen items-center justify-center bg-white dark:bg-gray-900">
        <div className="text-gray-400 dark:text-gray-500">Loading...</div>
      </div>
    );
  }

  const showFileUpload = appState === "no-file" || showDropZone;

  return (
    <Layout
      conversations={conversations}
      activeConversationId={activeId}
      onSelectConversation={handleSelectConversation}
      onNewConversation={handleNewConversation}
      onDeleteConversation={handleDelete}
    >
      <div className="flex flex-1 overflow-hidden">
        <div className="flex flex-1 flex-col overflow-hidden">
          {showFileUpload ? (
            <FileDropZone
              onFile={handleFile}
              uploading={uploading}
              progress={progress}
              error={uploadError}
            />
          ) : (
            <ChatWindow
              messages={messages}
              toolStatus={toolStatus}
              isLoading={isLoading}
              inputDisabled={!activeId}
              onSubmit={handleSubmit}
              onStop={stop}
              onVizClick={handleVizClick}
              showSuggestions={showSuggestions}
            />
          )}
        </div>
        {vizDisplay && (
          <VizPanel display={vizDisplay} sql={vizSql} onClose={handleVizClose} />
        )}
      </div>
    </Layout>
  );
}

export default App;
