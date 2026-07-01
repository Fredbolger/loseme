'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api-client';
import type { SearchResultRaw, SessionSummary, DocumentPart, SourceRef } from '@/lib/types';

export function useConversations() {
  return useQuery({
    queryKey: ['search', 'history'],
    queryFn: () => api.get<{ sessions: SessionSummary[] }>('/search/history?limit=50'),
  });
}

export function useConversationDetail(sessionId: string | null) {
  return useQuery({
    queryKey: ['search', 'session', sessionId],
    queryFn: () => api.get(`/search/sessions/${sessionId}`),
    enabled: !!sessionId,
  });
}

export function useDeleteConversation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (sessionId: string) => api.delete(`/search/sessions/${sessionId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['search', 'history'] }),
  });
}

export function useLLMModels() {
  return useQuery({
    queryKey: ['llm', 'models'],
    queryFn: () => api.get<string[]>('/llm/models'),
    staleTime: 60_000,
    retry: 0,
  });
}

interface SearchResponse {
  session_id: string;
  results: SearchResultRaw[];
  cache_hit: boolean;
  is_continuation: boolean;
}

export async function performSearch(query: string, topK: number, sessionId: string | null) {
  const body: Record<string, unknown> = { query, top_k: topK };
  if (sessionId) body.session_id = sessionId;
  return api.post<SearchResponse>('/search', body);
}

export async function batchGetDocuments(partIds: string[]): Promise<Record<string, DocumentPart>> {
  if (!partIds.length) return {};
  try {
    const res = await api.post<{ documents_parts: DocumentPart[] }>('/documents/batch_get', {
      document_part_ids: partIds,
    });
    const enriched: Record<string, DocumentPart> = {};
    res.documents_parts.forEach((p) => {
      enriched[p.document_part_id] = p;
    });
    return enriched;
  } catch {
    return {};
  }
}

export async function saveAnswer(
  sessionId: string,
  answer: string,
  resultIds: string[],
  sources: SourceRef[],
) {
  return api.post(`/search/sessions/${sessionId}/answer`, {
    answer,
    search_results_used: resultIds,
    sources,
  });
}
