import type { ReactNode } from "react";
import { useCallback, useEffect, useState } from "react";
import { Header } from "./Header";
import { Sidebar } from "./Sidebar";
import type { ConversationResponse } from "../../lib/types";

const MOBILE_BREAKPOINT = 768;

function useIsMobile(): boolean {
  const [isMobile, setIsMobile] = useState(
    () => window.innerWidth < MOBILE_BREAKPOINT,
  );

  useEffect(() => {
    const mql = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT - 1}px)`);
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, []);

  return isMobile;
}

interface LayoutProps {
  children: ReactNode;
  conversations: ConversationResponse[];
  activeConversationId: string | null;
  onSelectConversation: (id: string) => void;
  onNewConversation: () => void;
  onDeleteConversation: (id: string) => void;
}

export function Layout({
  children,
  conversations,
  activeConversationId,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
}: LayoutProps) {
  const isMobile = useIsMobile();
  const [sidebarOpen, setSidebarOpen] = useState(() => !isMobile);

  useEffect(() => {
    setSidebarOpen(!isMobile);
  }, [isMobile]);

  const handleSelectConversation = useCallback(
    (id: string) => {
      onSelectConversation(id);
      if (isMobile) setSidebarOpen(false);
    },
    [isMobile, onSelectConversation],
  );

  return (
    <div className="flex h-screen flex-col bg-white dark:bg-gray-900">
      <Header
        onToggleSidebar={() => setSidebarOpen((o) => !o)}
        sidebarOpen={sidebarOpen}
      />
      <div className="relative flex flex-1 overflow-hidden">
        {/* Mobile: overlay with slide transition */}
        {isMobile && (
          <>
            <div
              className={`absolute inset-0 z-20 bg-black/40 transition-opacity duration-200 ${
                sidebarOpen
                  ? "opacity-100"
                  : "pointer-events-none opacity-0"
              }`}
              onClick={() => setSidebarOpen(false)}
            />
            <div
              className={`absolute inset-y-0 left-0 z-30 transition-transform duration-200 ease-in-out ${
                sidebarOpen ? "translate-x-0" : "-translate-x-full"
              }`}
            >
              <Sidebar
                conversations={conversations}
                activeId={activeConversationId}
                onSelect={handleSelectConversation}
                onNew={onNewConversation}
                onDelete={onDeleteConversation}
              />
            </div>
          </>
        )}
        {/* Desktop: inline push behavior */}
        {!isMobile && sidebarOpen && (
          <Sidebar
            conversations={conversations}
            activeId={activeConversationId}
            onSelect={handleSelectConversation}
            onNew={onNewConversation}
            onDelete={onDeleteConversation}
          />
        )}
        <main className="flex flex-1 flex-col overflow-hidden">
          {children}
        </main>
      </div>
    </div>
  );
}
