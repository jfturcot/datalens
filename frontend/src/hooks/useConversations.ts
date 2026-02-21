import { useCallback, useState } from "react";
import {
  deleteConversation,
  getConversation,
  listConversations,
} from "../lib/api";
import { extractDisplay } from "../lib/displayExtractor";
import type {
  ChatMessage,
  ConversationResponse,
} from "../lib/types";

interface UseConversationsReturn {
  conversations: ConversationResponse[];
  activeId: string | null;
  loading: boolean;
  setActiveId: (id: string | null) => void;
  refresh: () => Promise<void>;
  loadHistory: (id: string) => Promise<ChatMessage[]>;
  remove: (id: string) => Promise<void>;
}

export function useConversations(): UseConversationsReturn {
  const [conversations, setConversations] = useState<ConversationResponse[]>(
    [],
  );
  const [activeId, setActiveId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const list = await listConversations();
      setConversations(list);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadHistory = useCallback(async (id: string): Promise<ChatMessage[]> => {
    const detail = await getConversation(id);
    return detail.messages.map((m, i) => {
      let display = m.display;
      let content = m.content;
      const sql = m.sql;

      // Fallback: extract display from content if backend didn't provide it
      if (!display && m.role === "assistant") {
        const extracted = extractDisplay(content);
        display = extracted.display ?? undefined;
        content = extracted.cleanedContent;
      }

      return {
        id: `history-${i}`,
        role: m.role as "user" | "assistant",
        content,
        sql,
        display,
      };
    });
  }, []);

  const remove = useCallback(
    async (id: string) => {
      await deleteConversation(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (activeId === id) {
        setActiveId(null);
      }
    },
    [activeId],
  );

  return {
    conversations,
    activeId,
    loading,
    setActiveId,
    refresh,
    loadHistory,
    remove,
  };
}
