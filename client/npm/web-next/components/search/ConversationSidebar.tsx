'use client';

import { useState } from 'react';
import { Plus, Trash2, PanelLeftClose, PanelLeftOpen, MessageSquare, Search } from 'lucide-react';
import { useConversations, useDeleteConversation } from '@/hooks/useSearch';
import { fmtDate } from '@/lib/format';
import { Button } from '@/components/ui/Button';
import { EmptyState, LoadingState } from '@/components/ui/States';
import { cn } from '@/lib/cn';

interface ConversationSidebarProps {
  activeSessionId: string | null;
  onSelect: (sessionId: string) => void;
  onNewChat: () => void;
  onLoadConversation?: (sessionId: string) => void;
}

export function ConversationSidebar({ activeSessionId, onSelect, onNewChat, onLoadConversation }: ConversationSidebarProps) {
  const [collapsed, setCollapsed] = useState(false);
  const conversationsQ = useConversations();
  const deleteMutation = useDeleteConversation();

  return (
    <aside
      className={cn(
        'flex flex-shrink-0 flex-col overflow-hidden border-r border-border bg-bg-secondary transition-[width] duration-300',
        collapsed ? 'w-[48px]' : 'w-[280px]',
      )}
    >
      {/* === HEADER === */}
      <div className="flex flex-col gap-2.5 border-b border-border p-3">
        {/* Top row: title + toggle button */}
        <div
          className={cn(
            'flex items-center',
            collapsed ? 'justify-center' : 'justify-between',
          )}
        >
          <h2
            className={cn(
              'flex items-center gap-1.5 text-[13px] font-semibold text-text-secondary transition-all duration-300 overflow-hidden whitespace-nowrap',
              collapsed ? 'w-0 opacity-0' : 'w-auto opacity-100',
            )}
          >
            <MessageSquare size={14} /> Conversations
          </h2>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setCollapsed((c) => !c)}
            className="flex-shrink-0"
          >
            {collapsed ? <PanelLeftOpen size={15} /> : <PanelLeftClose size={15} />}
          </Button>
        </div>

        {/* "New chat" button – fades & shrinks when collapsed */}
        <div
          className={cn(
            'transition-all duration-300 overflow-hidden',
            collapsed ? 'h-0 opacity-0' : 'h-auto opacity-100',
          )}
        >
          <Button variant="primary" size="sm" onClick={onNewChat} className="w-full">
            <Plus size={14} /> New chat
          </Button>
        </div>
      </div>

      {/* === CONVERSATION LIST === */}
      {/* Always rendered – just hidden when collapsed, so no sudden pop‑in */}
      <div
        className={cn(
          'flex-1 overflow-y-auto overflow-x-hidden p-2 transition-all duration-300 ease-out',
          collapsed
            ? 'opacity-0 pointer-events-none translate-x-2'
            : 'opacity-100 translate-x-0',
        )}
      >
        {/* This inner div keeps the layout fixed to 280px, so text never reflows */}
        <div className="w-full">
          {conversationsQ.isLoading ? (
            <LoadingState />
          ) : !conversationsQ.data?.sessions.length ? (
            <EmptyState
              icon="💬"
              title="No conversations yet"
              subtitle="Start a new search to begin"
            />
          ) : (
            <div className="flex flex-col gap-1">
              {conversationsQ.data.sessions.map((s) => (
                <button
                  key={s.session_id}
                  onClick={() => {
                    onSelect(s.session_id);
                    onLoadConversation?.(s.session_id);
                  }}
                  className={cn(
                    'group flex flex-col gap-1 rounded-md px-3 py-2.5 text-left transition-colors',
                    s.session_id === activeSessionId ? 'bg-bg-active' : 'hover:bg-bg-hover',
                  )}
                >
                  <div className="flex items-center gap-2">
                    <MessageSquare size={12} className="flex-shrink-0 text-text-tertiary" />
                    <span className="flex-1 truncate text-[12.5px] font-medium text-text-primary">
                      {s.title || s.query}
                    </span>
                    <span
                      role="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteMutation.mutate(s.session_id);
                      }}
                      className="flex-shrink-0 rounded p-1 text-text-tertiary opacity-0 transition-opacity hover:bg-bg-hover hover:text-status-error group-hover:opacity-100"
                    >
                      <Trash2 size={12} />
                    </span>
                  </div>
                  <div className="flex items-center justify-between pl-[18px] text-[10.5px] text-text-tertiary">
                    <span>{s.message_count} messages</span>
                    <span>{fmtDate(s.updated_at)}</span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
