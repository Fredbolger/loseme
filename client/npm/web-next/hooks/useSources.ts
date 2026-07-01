'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api-client';
import type { Chunk, DocumentPart, MonitoredSource } from '@/lib/types';

export function useSources() {
  return useQuery({
    queryKey: ['sources', 'all'],
    queryFn: () => api.get<{ sources: MonitoredSource[] }>('/sources/get_all_sources'),
  });
}

export function useDocumentsBySource(sourceId: string | null) {
  return useQuery({
    queryKey: ['documents', 'by_source', sourceId],
    queryFn: () => api.get<{ documents: DocumentPart[] }>(`/documents/by_source/${sourceId}`),
    enabled: !!sourceId,
  });
}

export function useDocumentDetail(docId: string | null) {
  return useQuery({
    queryKey: ['documents', 'detail', docId],
    queryFn: () => api.get<{ document_part: DocumentPart }>(`/documents/${docId}`),
    enabled: !!docId,
  });
}

export function useDocumentChunks(docId: string | null, enabled: boolean) {
  return useQuery({
    queryKey: ['documents', 'chunks', docId],
    queryFn: () => api.get<{ chunks: Chunk[] }>(`/documents/${docId}/chunks`),
    enabled: !!docId && enabled,
  });
}

export function usePreview(docId: string | null) {
  return useQuery({
    queryKey: ['preview', docId],
    queryFn: () => api.get<Record<string, unknown>>(`/documents/preview/${docId}`),
    enabled: !!docId,
  });
}
