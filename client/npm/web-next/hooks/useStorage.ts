'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api-client';
import type { ChunkDistributionResponse, ChunkerStat } from '@/lib/types';

export function useChunkerStats() {
  return useQuery({
    queryKey: ['documents', 'stats', 'chunker'],
    queryFn: () => api.get<{ stats: ChunkerStat[] }>('/documents/stats/chunker'),
  });
}

export function useChunkDistribution(chunkerName: string) {
  return useQuery({
    queryKey: ['chunks', 'distribution', chunkerName],
    queryFn: () =>
      api.get<ChunkDistributionResponse>(
        chunkerName === 'all'
          ? '/chunks/stats/distribution'
          : `/chunks/stats/distribution?chunker_name=${encodeURIComponent(chunkerName)}`,
      ),
  });
}

export function useTotalChunkCount() {
  return useQuery({
    queryKey: ['chunks', 'count'],
    queryFn: () => api.get<{ number_of_chunks: number }>('/chunks/number_of_chunks'),
  });
}
