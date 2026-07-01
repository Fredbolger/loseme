'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { api } from '@/lib/api-client';
import type { IndexingRunSummary } from '@/lib/types';

export function useRuns() {
  return useQuery({
    queryKey: ['runs', 'list'],
    queryFn: () => api.get<{ runs: IndexingRunSummary[] }>('/runs/list'),
    refetchInterval: 60_000,
  });
}

function useRunMutation(
  fn: (runId: string) => Promise<unknown>,
  successMsg: (runId: string) => string,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: (_d, runId) => {
      toast.success(successMsg(runId));
      qc.invalidateQueries({ queryKey: ['runs', 'list'] });
    },
    onError: (err: Error) => toast.error(err.message),
  });
}

export function useStopRun() {
  return useRunMutation(
    (id) => api.post(`/runs/request_stop/${id}`),
    () => 'Run stopped',
  );
}

export function useResumeRun() {
  return useRunMutation(
    (id) => api.post(`/runs/resume/${id}`),
    () => 'Run resumed',
  );
}

export function useDeleteRun() {
  return useRunMutation(
    (id) => api.post(`/runs/delete/${id}`),
    () => 'Run deleted',
  );
}

export function useStopAllRuns() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post('/runs/stop_all'),
    onSuccess: () => {
      toast.success('Stop requested for all active runs');
      qc.invalidateQueries({ queryKey: ['runs', 'list'] });
    },
    onError: (err: Error) => toast.error(err.message),
  });
}
