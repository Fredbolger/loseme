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

/** Triggers local ingestion via the Next.js proxy route to the ingest sidecar (mirrors POST /sources/scan/{id} in old main.py). */
export function useScanSource() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ sourceId, forceReprocess }: { sourceId: string; forceReprocess: boolean }) => {
      console.log('[DEBUG] useScanSource called', { sourceId, forceReprocess });
      const clientBase = await getClientBase();
      console.log('[DEBUG] Client base URL:', clientBase);
      
      const startTime = Date.now();
      const res = await fetch(
        `${clientBase}/api/sources/scan/${sourceId}?force_reprocess=${forceReprocess}`,
        { method: 'POST' },
      );
      const duration = Date.now() - startTime;
      
      console.log('[DEBUG] Scan response received', {
        status: res.status,
        statusText: res.statusText,
        durationMs: duration
      });
      
      if (res.status === 403) {
        const data = await res.json();
        console.log('[DEBUG] 403 Forbidden - Wrong device:', data);
        throw new Error(data.detail || 'Cannot scan source that belongs to another device');
      }
      if (!res.ok) {
        const errorText = await res.text();
        console.log('[DEBUG] Scan failed:', res.status, errorText);
        throw new Error(`Scan failed: HTTP ${res.status}`);
      }
      
      const responseData = await res.json();
      console.log('[DEBUG] Scan successful, response:', responseData);
      return responseData;
    },
    onSuccess: (_data, vars) => {
      console.log('[DEBUG] Scan mutation successful', vars);
      toast.success(vars.forceReprocess ? 'Queued (forced re-index)' : 'Scan queued');
      qc.invalidateQueries({ queryKey: ['documents'] });
    },
    onError: (err: Error) => {
      console.log('[DEBUG] Scan mutation error:', err.message);
      toast.error(err.message);
    },
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
