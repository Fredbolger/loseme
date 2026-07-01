'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { api, getClientBase } from '@/lib/api-client';
import type { DocumentStats, MonitoredSource, StatsPerSource } from '@/lib/types';

export function useDocumentStats() {
  return useQuery({
    queryKey: ['documents', 'stats'],
    queryFn: () => api.get<DocumentStats>('/documents/stats'),
  });
}

export function useChunkCount() {
  return useQuery({
    queryKey: ['chunks', 'count'],
    queryFn: () => api.get<{ number_of_chunks: number }>('/chunks/number_of_chunks'),
  });
}

export function useAllSources() {
  return useQuery({
    queryKey: ['sources', 'all'],
    queryFn: () => api.get<{ sources: MonitoredSource[] }>('/sources/get_all_sources'),
  });
}

export function useStatsPerSource() {
  return useQuery({
    queryKey: ['documents', 'stats', 'per_source'],
    queryFn: () => api.get<{ stats_per_source: StatsPerSource[] }>('/documents/stats/per_source'),
  });
}

/** Triggers local ingestion via the client-local route (mirrors POST /sources/scan/{id} in old main.py). */
export function useScanSource() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ sourceId, forceReprocess }: { sourceId: string; forceReprocess: boolean }) => {
      const clientBase = await getClientBase();
      const res = await fetch(
        `${clientBase}/api/sources/scan/${sourceId}?force_reprocess=${forceReprocess}`,
        { method: 'POST' },
      );
      if (res.status === 403) {
        const data = await res.json();
        throw new Error(data.detail || 'Cannot scan source that belongs to another device');
      }
      if (!res.ok) throw new Error(`Scan failed: HTTP ${res.status}`);
      return res.json();
    },
    onSuccess: (_data, vars) => {
      toast.success(vars.forceReprocess ? 'Queued (forced re-index)' : 'Scan queued');
      qc.invalidateQueries({ queryKey: ['documents'] });
    },
    onError: (err: Error) => toast.error(err.message),
  });
}

export function useDeleteSource() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (sourceId: string) =>
      api.get(`/sources/delete/${sourceId}?dry_run=false&confirm=true`),
    onSuccess: () => {
      toast.success('Source deleted');
      qc.invalidateQueries({ queryKey: ['sources'] });
      qc.invalidateQueries({ queryKey: ['documents'] });
    },
    onError: (err: Error) => toast.error(err.message),
  });
}
