import { create } from 'zustand';
import type { ChatMessage, MergedSearchResult, SourceRef } from './types';

interface SearchState {
  sessionId: string | null;
  messages: ChatMessage[];
  lastResults: MergedSearchResult[];
  lastEnriched: Record<string, { source_path?: string }>;
  isAwaitingResponse: boolean;
  selectedModel: string | null;
  availableModels: string[];
  searchMode: 'hybrid' | 'search';
  topK: number;
  sourcesPanelOpen: boolean;
  // Streaming buffer — kept here (not component state) so a tab switch
  // doesn't lose an in-flight answer, mirroring the legacy pendingAnswer/
  // pendingMessageId pattern but without the manual isMounted bookkeeping.
  streamingMessageId: string | null;
  streamingContent: string;

  setSession: (id: string | null) => void;
  addMessage: (msg: ChatMessage) => void;
  updateMessage: (id: string, content: string) => void;
  setMessages: (msgs: ChatMessage[]) => void;
  setLastResults: (results: MergedSearchResult[], enriched: Record<string, { source_path?: string }>) => void;
  setAwaiting: (v: boolean) => void;
  setModel: (m: string | null) => void;
  setAvailableModels: (models: string[]) => void;
  setSearchMode: (m: 'hybrid' | 'search') => void;
  setTopK: (k: number) => void;
  setSourcesPanelOpen: (v: boolean) => void;
  setStreaming: (id: string | null, content: string) => void;
  appendStreaming: (token: string) => void;
  reset: () => void;
}

const initial = {
  sessionId: null,
  messages: [],
  lastResults: [],
  lastEnriched: {},
  isAwaitingResponse: false,
  selectedModel: null,
  availableModels: [],
  searchMode: 'hybrid' as const,
  topK: 10,
  sourcesPanelOpen: false,
  streamingMessageId: null,
  streamingContent: '',
};

export const useSearchStore = create<SearchState>((set) => ({
  ...initial,

  setSession: (id) => set({ sessionId: id }),
  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
  updateMessage: (id, content) =>
    set((s) => ({ messages: s.messages.map((m) => (m.id === id ? { ...m, content } : m)) })),
  setMessages: (msgs) => set({ messages: msgs }),
  setLastResults: (results, enriched) => set({ lastResults: results, lastEnriched: enriched }),
  setAwaiting: (v) => set({ isAwaitingResponse: v }),
  setModel: (m) => set({ selectedModel: m }),
  setAvailableModels: (models) => set({ availableModels: models }),
  setSearchMode: (m) => set({ searchMode: m }),
  setTopK: (k) => set({ topK: k }),
  setSourcesPanelOpen: (v) => set({ sourcesPanelOpen: v }),
  setStreaming: (id, content) => set({ streamingMessageId: id, streamingContent: content }),
  appendStreaming: (token) => set((s) => ({ streamingContent: s.streamingContent + token })),
  reset: () =>
    set({
      sessionId: null,
      messages: [],
      lastResults: [],
      lastEnriched: {},
      streamingMessageId: null,
      streamingContent: '',
    }),
}));
