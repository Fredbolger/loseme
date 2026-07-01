'use client';

import { useEffect, useState } from 'react';
import { toast } from 'sonner';
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
import { ConversationSidebar } from '@/components/search/ConversationSidebar';
import { ChatMessage } from '@/components/search/ChatMessage';
import { ChatInputBar } from '@/components/search/ChatInputBar';
import { WelcomeScreen } from '@/components/search/WelcomeScreen';
import { SourcesPanel } from '@/components/search/SourcesPanel';
import type { ChatMessage as ChatMessageType, SourceRef } from '@/lib/types';

export default function SearchPage() {
  const store = useSearchStore();
  const { stream, isStreaming } = useSSEStream();
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

  const conversationDetailQ = useConversationDetail(store.sessionId);

  // When switching to a session via the sidebar (not via an active local
  // search), hydrate the message list from the server.
  useEffect(() => {
    if (!conversationDetailQ.data) return;
    const detail = conversationDetailQ.data as {
      messages: { id: string; role: string; content: string; sources?: SourceRef[]; created_at: string }[];
    };
    // Only hydrate if our local message list doesn't already match (avoids
    // clobbering an in-progress conversation we just created locally).
    if (store.messages.length === 0 || store.messages[0]?.id !== detail.messages[0]?.id) {
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
    }
  }, [conversationDetailQ.data]); // eslint-disable-line react-hooks/exhaustive-deps

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
      const searchRes = await performSearch(query, store.topK, store.sessionId);
      store.setSession(searchRes.session_id);

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
        if (store.sessionId) {
          await saveAnswer(
            store.sessionId,
            assistantMsg.content,
            merged.slice(0, store.topK).map((d) => d.document_part_id),
            sourcesToStore,
          );
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
        const assistantMsg: ChatMessageType = {
          id: assistantId,
          role: 'assistant',
          content: finalContent,
          sources: sourcesToStore,
          created_at: new Date().toISOString(),
        };
        store.addMessage(assistantMsg);
        store.setStreaming(null, '');

        if (store.sessionId && finalContent.trim()) {
          await saveAnswer(
            store.sessionId,
            finalContent,
            merged.slice(0, store.topK).map((d) => d.document_part_id),
            sourcesToStore,
          );
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
