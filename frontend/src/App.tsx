import { useCallback, useEffect, useRef, useState } from "react";
import { Layout } from "./components/layout/Layout";
import { FileDropZone } from "./components/chat/FileDropZone";
import { ChatWindow } from "./components/chat/ChatWindow";
import { VizPanel } from "./components/viz/VizPanel";
import { createSession, getMySession } from "./lib/api";
import { useChat } from "./hooks/useChat";
import { useFileUpload } from "./hooks/useFileUpload";
import { useConversations } from "./hooks/useConversations";
import type { ColumnInfo, DisplayData } from "./lib/types";

type AppState = "loading" | "no-file" | "chat";

function formatGreeting(filename: string, columns: ColumnInfo[], rowCount: number): string {
  const colList = columns.map((c) => `  - ${c.name} (${c.type})`).join("\n");
  return `I've loaded **${filename}** — ${rowCount.toLocaleString()} rows with ${columns.length} columns:\n\n${colList}\n\nWhat would you like to know about this data?`;
}

function App() {
  const [appState, setAppState] = useState<AppState>("loading");
  const [sessionReady, setSessionReady] = useState(false);
  const [showDropZone, setShowDropZone] = useState(false);
  const [vizDisplay, setVizDisplay] = useState<DisplayData | null>(null);
  const initRef = useRef(false);

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
      setActiveId(result.conversation_id);
      setShowDropZone(false);

      const greeting = formatGreeting(
        result.filename,
        result.columns,
        result.row_count,
      );
      setMessages([
        {
          id: `greeting-${Date.now()}`,
          role: "assistant",
          content: greeting,
        },
      ]);
      setAppState("chat");
    },
    [upload, refresh, setActiveId, setMessages],
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

  const handleVizClick = useCallback((display: DisplayData) => {
    setVizDisplay(display);
  }, []);

  const handleVizClose = useCallback(() => {
    setVizDisplay(null);
  }, []);

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
            />
          )}
        </div>
        {vizDisplay && (
          <VizPanel display={vizDisplay} onClose={handleVizClose} />
        )}
      </div>
    </Layout>
  );
}

export default App;
