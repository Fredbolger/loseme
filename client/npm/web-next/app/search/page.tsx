'use client';

import { useEffect, useState, useCallback } from 'react';
import { toast } from 'sonner';
import { useQueryClient } from '@tanstack/react-query';
import { useSearchStore } from '@/lib/search-store';
import { useDetailPanelStore } from '@/lib/detail-panel-store';
import { mergeByPart, buildLLMContext } from '@/lib/merge-search-results';
import {
  performSearch,
  batchGetDocuments,
  saveAnswer,
  useLLMModels,
  useConversationDetail,
} from '@/hooks/useSearch';
import { useSSEStream } from '@/hooks/useSSEStream';
import { api } from '@/lib/api-client';
import { ConversationSidebar } from '@/components/search/ConversationSidebar';
import { ChatMessage } from '@/components/search/ChatMessage';
import { ChatInputBar } from '@/components/search/ChatInputBar';
import { WelcomeScreen } from '@/components/search/WelcomeScreen';
import { SourcesPanel } from '@/components/search/SourcesPanel';
import type { ChatMessage as ChatMessageType, SourceRef } from '@/lib/types';

export default function SearchPage() {
  const queryClient = useQueryClient();
  const store = useSearchStore();
  const { stream, isStreaming, abort } = useSSEStream();
  const modelsQ = useLLMModels();
  const openDetail = useDetailPanelStore((s) => s.open);

  const [draft, setDraft] = useState('');
  const [activeSourcesForPanel, setActiveSourcesForPanel] = useState<SourceRef[]>([]);

  // Seed default model once models load.
  useEffect(() => {
    if (modelsQ.data?.length && !store.selectedModel) {
      store.setModel(modelsQ.data[0]!);
      store.setAvailableModels(modelsQ.data);
    }
  }, [modelsQ.data]); // eslint-disable-line react-hooks/exhaustive-deps

  // Explicit loadConversation function - only called when user selects a conversation from sidebar
  const loadConversation = useCallback(async (sessionId: string) => {
    // Abort any in-flight SSE stream to avoid stale stream writing to wrong session
    abort();
    
    try {
      const detail = await api.get<{
        messages: { id: string; role: string; content: string; sources?: SourceRef[]; created_at: string }[]
      }>(`/search/sessions/${sessionId}`);
      
      store.setMessages(
        detail.messages
          .filter((m) => m.role === 'user' || m.role === 'assistant')
          .map((m) => ({
            id: m.id,
            role: m.role as 'user' | 'assistant',
            content: m.content,
            sources: m.sources,
            created_at: m.created_at,
          })),
      );
    } catch (error) {
      toast.error('Failed to load conversation');
      console.error('Failed to load conversation:', error);
    }
  }, [store, abort]);


  function openSourcesPanel(sources: SourceRef[]) {
    setActiveSourcesForPanel(sources);
    store.setSourcesPanelOpen(true);
  }

  function openDocFromSource(source: SourceRef) {
    const docs = store.lastResults.map((d) => ({
      document_part_id: d.document_part_id,
      source_type: d.source_type,
      source_path: d.source_path,
    }));
    openDetail(source.document_part_id, docs.length ? docs : [
      { document_part_id: source.document_part_id, source_type: source.source_type, source_path: source.source_path },
    ]);
  }

  async function handleSend() {
    const query = draft.trim();
    if (!query || store.isAwaitingResponse) return;

    // Abort any in-flight SSE stream before starting a new search
    abort();
    setDraft('');
    const userMsg: ChatMessageType = {
      id: crypto.randomUUID(),
      role: 'user',
      content: query,
      created_at: new Date().toISOString(),
    };
    store.addMessage(userMsg);
    store.setAwaiting(true);

    try {
      const searchRes = await performSearch(query, store.topK, store.sessionId, queryClient);
      if (!searchRes?.session_id) {
        toast.error(`Server did not return session_id: ${JSON.stringify(searchRes)}`);
      } else {
        toast.success(`Session created: ${searchRes.session_id.slice(0, 8)}...`);
      }
      const sid = searchRes.session_id;
      store.setSession(sid);
      // Use getState() to get the current value from the global store
      const currentSessionId = useSearchStore.getState().sessionId;
      if (!currentSessionId) {
        toast.error(`CRITICAL: sessionId not set! sid=${sid?.slice(0, 8) || 'NULL'}, current=${currentSessionId}`);
      }

      const merged = mergeByPart(searchRes.results);
      const partIds = [...new Set(searchRes.results.map((r) => r.document_part_id))];
      const enriched = partIds.length ? await batchGetDocuments(partIds) : {};
      store.setLastResults(merged, enriched);

      const sourcesToStore: SourceRef[] = merged.slice(0, store.topK).map((doc) => ({
        document_part_id: doc.document_part_id,
        source_path: doc.source_path,
        source_type: doc.source_type,
        score: doc.maxScore,
        chunk_count: doc.chunkCount,
      }));

      if (store.searchMode === 'search') {
        // Search-only mode: no LLM call, just report what was found.
        const assistantMsg: ChatMessageType = {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: `Found ${merged.length} relevant document${merged.length !== 1 ? 's' : ''}.`,
          sources: sourcesToStore,
          created_at: new Date().toISOString(),
        };
        store.addMessage(assistantMsg);
        const currentSessionId = useSearchStore.getState().sessionId;
        if (currentSessionId) {
          await saveAnswer(
            currentSessionId,
            assistantMsg.content,
            merged.slice(0, store.topK).map((d) => d.document_part_id),
            sourcesToStore,
          );
          toast.success('Search mode: Assistant message saved');
        } else {
          toast.error('Search mode: Failed to save - sessionId not set');
        }
      } else {
        // Hybrid mode: stream the LLM answer token by token.
        const context = buildLLMContext(merged, enriched, store.messages.map((m) => ({ role: m.role, content: m.content })));
        const assistantId = crypto.randomUUID();
        store.setStreaming(assistantId, '');

        await stream(
          {
            query,
            context,
            topK: store.topK,
            model: store.selectedModel || 'mistral:7b',
            resultIds: merged.slice(0, store.topK).map((d) => d.document_part_id),
            sessionId: store.sessionId,
          },
          (token) => store.appendStreaming(token),
        );

        const finalContent = useSearchStore.getState().streamingContent;
        // Use fallback message if LLM returned empty content
        const assistantContent = finalContent.trim() || `Found ${merged.length} relevant document${merged.length !== 1 ? 's' : ''}.`;
        const assistantMsg: ChatMessageType = {
          id: assistantId,
          role: 'assistant',
          content: assistantContent,
          sources: sourcesToStore,
          created_at: new Date().toISOString(),
        };
        store.addMessage(assistantMsg);
        store.setStreaming(null, '');

        const currentSessionId = useSearchStore.getState().sessionId;
        if (currentSessionId) {
          await saveAnswer(
            currentSessionId,
            assistantContent,
            merged.slice(0, store.topK).map((d) => d.document_part_id),
            sourcesToStore,
          );
          toast.success('Assistant message saved to history');
        } else {
          toast.error('Failed to save: sessionId is not set');
        }
      }
    } catch (e) {
      toast.error((e as Error).message || 'Search failed');
      store.addMessage({
        id: crypto.randomUUID(),
        role: 'assistant',
        content: `❌ Error: ${(e as Error).message}`,
        created_at: new Date().toISOString(),
      });
    } finally {
      store.setAwaiting(false);
    }
  }

  function handleNewChat() {
    // Abort any in-flight SSE stream when starting a new chat
    abort();
    store.reset();
  }

  return (
    <div className="flex h-[calc(100vh-52px)] overflow-hidden">
      <ConversationSidebar
        activeSessionId={store.sessionId}
        onSelect={(id) => {
          store.setMessages([]);
          store.setSession(id);
        }}
        onNewChat={handleNewChat}
        onLoadConversation={loadConversation}
      />

      <div className="flex flex-1 flex-col overflow-hidden">
        <div className="flex flex-col overflow-y-auto px-6 py-6">
          {store.messages.length === 0 ? (
            <WelcomeScreen onPick={(text) => setDraft(text)} />
          ) : (
            <div className="mx-auto flex w-full max-w-3xl flex-col gap-5">
              {store.messages.map((m) => (
                <ChatMessage
                  key={m.id}
                  message={m}
                  streamingContent={m.id === store.streamingMessageId ? store.streamingContent : undefined}
                  onSourcesClick={openSourcesPanel}
                />
              ))}
              {store.streamingMessageId &&
                !store.messages.some((m) => m.id === store.streamingMessageId) && (
                  <ChatMessage
                    key={store.streamingMessageId}
                    message={{
                      id: store.streamingMessageId,
                      role: 'assistant',
                      content: store.streamingContent,
                      created_at: new Date().toISOString(),
                    }}
                    streamingContent={store.streamingContent}
                  />
                )}
            </div>
          )}
        </div>

        <ChatInputBar
          value={draft}
          onChange={setDraft}
          onSend={handleSend}
          disabled={store.isAwaitingResponse || isStreaming}
          models={store.availableModels}
        />
      </div>

      <SourcesPanel
        open={store.sourcesPanelOpen}
        sources={activeSourcesForPanel}
        onClose={() => store.setSourcesPanelOpen(false)}
        onSelect={openDocFromSource}
      />
    </div>
  );
}
