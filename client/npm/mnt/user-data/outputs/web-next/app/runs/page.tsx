'use client';

import { useMemo, useState } from 'react';
import { useRuns, useStopRun, useResumeRun, useDeleteRun, useStopAllRuns } from '@/hooks/useRuns';
import { RunCard } from '@/components/runs/RunCard';
import { Button } from '@/components/ui/Button';
import { Select, TextInput } from '@/components/ui/Select';
import { SegmentedControl } from '@/components/ui/SegmentedControl';
import { EmptyState, LoadingState, ErrorState } from '@/components/ui/States';
import { RUN_STATUS_COLOR, RUN_STATUS_LABEL, RUN_STATUS_ORDER } from '@/lib/status-colors';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import type { IndexingRunSummary, RunStatus } from '@/lib/types';

type GroupMode = 'source' | 'status' | 'none';

export default function RunsPage() {
  const { data, isLoading, isError } = useRuns();
  const stopRun = useStopRun();
  const resumeRun = useResumeRun();
  const deleteRun = useDeleteRun();
  const stopAll = useStopAllRuns();

  const [groupMode, setGroupMode] = useState<GroupMode>('source');
  const [filterStatus, setFilterStatus] = useState<RunStatus | 'all'>('all');
  const [filterSource, setFilterSource] = useState<string>('all');
  const [search, setSearch] = useState('');
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);

  const runs = data?.runs ?? [];

  const sourceTypes = useMemo(
    () => Array.from(new Set(runs.map((r) => r.source_type))).sort(),
    [runs],
  );

  const filtered = useMemo(() => {
    return runs.filter((r) => {
      if (filterStatus !== 'all' && r.status !== filterStatus) return false;
      if (filterSource !== 'all' && r.source_type !== filterSource) return false;
      if (search && !r.run_id.toLowerCase().includes(search.toLowerCase())) return false;
      return true;
    });
  }, [runs, filterStatus, filterSource, search]);

  const sorted = useMemo(() => {
    return [...filtered].sort((a, b) => {
      const ao = RUN_STATUS_ORDER.indexOf(a.status);
      const bo = RUN_STATUS_ORDER.indexOf(b.status);
      if (ao !== bo) return ao - bo;
      return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
    });
  }, [filtered]);

  const statusCounts = useMemo(() => {
    const counts: Partial<Record<RunStatus, number>> = {};
    runs.forEach((r) => {
      counts[r.status] = (counts[r.status] ?? 0) + 1;
    });
    return counts;
  }, [runs]);

  const activeRuns = runs.filter((r) => r.status === 'running' || r.status === 'starting');

  const groups = useMemo(() => {
    if (groupMode === 'none') return [{ key: null, items: sorted }];
    const key = groupMode === 'source' ? 'source_type' : 'status';
    const map = new Map<string, IndexingRunSummary[]>();
    sorted.forEach((r) => {
      const k = String(r[key as keyof IndexingRunSummary]);
      if (!map.has(k)) map.set(k, []);
      map.get(k)!.push(r);
    });
    return Array.from(map.entries()).map(([key, items]) => ({ key, items }));
  }, [sorted, groupMode]);

  return (
    <div className="mx-auto max-w-6xl px-6 py-10">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="font-display text-lg font-bold text-text-primary">Indexing Runs</h1>
        {activeRuns.length > 0 && (
          <Button
            variant="danger"
            size="sm"
            onClick={() => stopAll.mutate()}
            disabled={stopAll.isPending}
          >
            ⏹ Stop All ({activeRuns.length})
          </Button>
        )}
      </div>

      {/* Toolbar */}
      <div className="mb-5 flex flex-wrap items-center gap-3 rounded-lg border border-border bg-bg-secondary p-3.5">
        <TextInput
          placeholder="Filter by run ID…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-48"
        />
        <Select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value as RunStatus | 'all')}>
          <option value="all">All statuses</option>
          {RUN_STATUS_ORDER.map((s) => (
            <option key={s} value={s}>
              {RUN_STATUS_LABEL[s]}
            </option>
          ))}
        </Select>
        <Select value={filterSource} onChange={(e) => setFilterSource(e.target.value)}>
          <option value="all">All sources</option>
          {sourceTypes.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </Select>
        <div className="ml-auto flex items-center gap-2">
          <span className="text-[11px] font-medium uppercase tracking-wide text-text-tertiary">
            Group by
          </span>
          <SegmentedControl
            value={groupMode}
            onChange={setGroupMode}
            options={[
              { value: 'source', label: 'Source' },
              { value: 'status', label: 'Status' },
              { value: 'none', label: 'None' },
            ]}
          />
        </div>
      </div>

      {/* Summary chips */}
      {runs.length > 0 && (
        <div className="mb-6 flex flex-wrap gap-2">
          {RUN_STATUS_ORDER.filter((s) => statusCounts[s]).map((s) => (
            <span
              key={s}
              className="inline-flex items-center gap-1.5 rounded-full border border-border bg-bg-tertiary px-3 py-1 text-[11px] text-text-secondary"
            >
              <span className="h-1.5 w-1.5 rounded-full" style={{ background: RUN_STATUS_COLOR[s] }} />
              {RUN_STATUS_LABEL[s]} <strong className="text-text-primary">{statusCounts[s]}</strong>
            </span>
          ))}
        </div>
      )}

      {/* Content */}
      {isLoading ? (
        <LoadingState label="Loading runs…" />
      ) : isError ? (
        <ErrorState message="Could not load indexing runs." />
      ) : !sorted.length ? (
        <EmptyState icon="⚙️" title="No runs match the current filters" />
      ) : (
        <div className="flex flex-col gap-8">
          {groups.map((group) => (
            <div key={group.key ?? 'all'}>
              {group.key && (
                <div className="mb-3 flex items-center gap-2 border-b border-border pb-2">
                  {groupMode === 'status' && (
                    <span
                      className="h-2 w-2 rounded-full"
                      style={{ background: RUN_STATUS_COLOR[group.key as RunStatus] }}
                    />
                  )}
                  <span className="text-[13px] font-semibold text-text-primary">
                    {groupMode === 'status' ? RUN_STATUS_LABEL[group.key as RunStatus] : group.key}
                  </span>
                  <span className="text-[11px] text-text-tertiary">
                    {group.items.length} run{group.items.length !== 1 ? 's' : ''}
                  </span>
                </div>
              )}
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
                {group.items.map((run) => (
                  <RunCard
                    key={run.run_id}
                    run={run}
                    pending={stopRun.isPending || resumeRun.isPending || deleteRun.isPending}
                    onStop={() => stopRun.mutate(run.run_id)}
                    onResume={() => resumeRun.mutate(run.run_id)}
                    onDelete={() => setDeleteTarget(run.run_id)}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      <ConfirmDialog
        open={deleteTarget !== null}
        onOpenChange={(o) => !o && setDeleteTarget(null)}
        title="Delete this run?"
        description="The run record will be permanently removed. This does not delete already-indexed documents."
        confirmLabel="Delete"
        destructive
        onConfirm={() => {
          if (deleteTarget) deleteRun.mutate(deleteTarget);
          setDeleteTarget(null);
        }}
      />
    </div>
  );
}
