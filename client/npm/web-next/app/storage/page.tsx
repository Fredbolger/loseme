'use client';

import { useMemo, useState } from 'react';
import { useChunkerStats, useChunkDistribution, useTotalChunkCount } from '@/hooks/useStorage';
import { ChunkerCard } from '@/components/storage/ChunkerCard';
import { HistogramBars } from '@/components/storage/HistogramBars';
import { StatTile } from '@/components/dashboard/StatTile';
import { SegmentedControl } from '@/components/ui/SegmentedControl';
import { Card } from '@/components/ui/Card';
import { EmptyState, LoadingState, ErrorState } from '@/components/ui/States';

export default function StoragePage() {
  const chunkerQ = useChunkerStats();
  const totalChunksQ = useTotalChunkCount();
  const [activeChunker, setActiveChunker] = useState('all');
  const distQ = useChunkDistribution(activeChunker);

  const stats = chunkerQ.data?.stats ?? [];
  const totalParts = useMemo(
    () => stats.reduce((sum, r) => sum + (r.document_part_count ?? 0), 0),
    [stats],
  );

  const chunkerOptions = useMemo(
    () => [
      { value: 'all', label: 'All' },
      ...stats.map((s) => ({ value: s.chunker_name ?? 'unknown', label: s.chunker_name ?? 'unknown' })),
    ],
    [stats],
  );

  const filteredStats =
    activeChunker === 'all' ? stats : stats.filter((s) => (s.chunker_name ?? 'unknown') === activeChunker);

  return (
    <div className="mx-auto max-w-5xl px-6 py-10">
      <h1 className="mb-6 font-display text-lg font-bold text-text-primary">Storage Overview</h1>

      <section className="mb-10 grid grid-cols-1 gap-3 sm:grid-cols-3">
        <StatTile label="Document Parts" value={totalParts.toLocaleString()} icon="📄" />
        <StatTile label="Total Chunks" value={totalChunksQ.data?.number_of_chunks?.toLocaleString() ?? '—'} icon="🧩" />
        <StatTile label="Chunker Versions" value={stats.length} icon="🔧" />
      </section>

      <section className="mb-10">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <h2 className="font-display text-base font-semibold text-text-primary">By Chunker</h2>
          {stats.length > 0 && (
            <SegmentedControl value={activeChunker} onChange={setActiveChunker} options={chunkerOptions} />
          )}
        </div>

        {chunkerQ.isLoading ? (
          <LoadingState />
        ) : chunkerQ.isError ? (
          <ErrorState message="Could not load chunker stats." />
        ) : !filteredStats.length ? (
          <EmptyState title="No chunker data available" />
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {filteredStats.map((s, i) => (
              <ChunkerCard key={`${s.chunker_name}-${s.chunker_version}-${i}`} stat={s} totalParts={totalParts} />
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="mb-4 font-display text-base font-semibold text-text-primary">Distributions</h2>

        {distQ.isLoading ? (
          <LoadingState label="Loading distributions…" />
        ) : distQ.isError ? (
          <ErrorState message="Could not load distribution data." />
        ) : (
          <>
            {distQ.data?.stats.count ? (
              <div className="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-5">
                <MiniStat label="Chunks" value={distQ.data.stats.count!.toLocaleString()} />
                <MiniStat label="Mean size" value={`${distQ.data.stats.mean} chars`} />
                <MiniStat label="p50" value={`${distQ.data.stats.p50} chars`} />
                <MiniStat label="p95" value={`${distQ.data.stats.p95} chars`} accent />
                <MiniStat label="Max" value={`${distQ.data.stats.max?.toLocaleString()} chars`} />
              </div>
            ) : null}

            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <Card>
                <h3 className="mb-3 text-[13px] font-semibold text-text-primary">Chunk size distribution</h3>
                <HistogramBars buckets={distQ.data?.char_len_histogram ?? []} />
              </Card>
              <Card>
                <h3 className="mb-3 text-[13px] font-semibold text-text-primary">Chunks per document</h3>
                <HistogramBars buckets={distQ.data?.chunks_per_doc_histogram ?? []} />
              </Card>
            </div>
          </>
        )}
      </section>
    </div>
  );
}

function MiniStat({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <Card className="flex flex-col gap-1 p-3">
      <span className="text-[10px] uppercase tracking-wide text-text-tertiary">{label}</span>
      <span className={accent ? 'font-display text-lg font-bold text-status-success' : 'font-display text-lg font-bold text-text-primary'}>
        {value}
      </span>
    </Card>
  );
}
