'use client';

import { useMemo, useState } from 'react';
import {
  useDocumentStats,
  useChunkCount,
  useAllSources,
  useStatsPerSource,
  useScanSource,
  useDeleteSource,
} from '@/hooks/useDashboard';
import { StatTile } from '@/components/dashboard/StatTile';
import { SourceTreeView } from '@/components/dashboard/SourceTreeView';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { EmptyState, LoadingState } from '@/components/ui/States';
import { Badge } from '@/components/ui/Badge';
import { enrichSources, buildSourceTree } from '@/lib/source-tree';

export default function DashboardPage() {
  const stats = useDocumentStats();
  const chunkCount = useChunkCount();
  const sourcesQ = useAllSources();
  const perSourceQ = useStatsPerSource();
  const scanMutation = useScanSource();
  const deleteMutation = useDeleteSource();

  const [scanTarget, setScanTarget] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);

  const tree = useMemo(() => {
    if (!sourcesQ.data) return [];
    const docCountMap: Record<string, number> = {};
    (perSourceQ.data?.stats_per_source || []).forEach((s) => {
      docCountMap[s.source_id] = s.document_part_count;
    });
    const enriched = enrichSources(sourcesQ.data.sources, docCountMap);
    return buildSourceTree(enriched);
  }, [sourcesQ.data, perSourceQ.data]);

  return (
    <div className="mx-auto max-w-5xl px-6 py-10">
      {/* Stats */}
      <section className="mb-10 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile label="Document Parts" value={stats.data?.total_document_parts ?? '—'} icon="📄" />
        <StatTile label="Total Chunks" value={chunkCount.data?.number_of_chunks ?? '—'} icon="🧩" />
        <StatTile label="Source Instances" value={stats.data?.total_sources ?? '—'} icon="📁" />
        <StatTile label="Devices" value={stats.data?.total_devices ?? '—'} icon="📱" />
      </section>

      {/* Sources */}
      <section>
        <div className="mb-4 flex items-center gap-2.5">
          <h1 className="font-display text-lg font-bold text-text-primary">Sources</h1>
          <Badge variant="outline">
            {sourcesQ.data?.sources.length ?? 0} source{sourcesQ.data?.sources.length !== 1 ? 's' : ''}
          </Badge>
        </div>

        {sourcesQ.isLoading ? (
          <LoadingState label="Loading sources…" />
        ) : !sourcesQ.data?.sources.length ? (
          <EmptyState
            icon="📁"
            title="No monitored sources yet"
            subtitle="Add a filesystem, Thunderbird, or Paperless source from the CLI to start indexing."
          />
        ) : (
          <SourceTreeView
            nodes={tree}
            onScan={(id) => setScanTarget(id)}
            onDelete={(id) => setDeleteTarget(id)}
          />
        )}
      </section>

      {/* Scan confirm */}
      <ConfirmDialog
        open={scanTarget !== null}
        onOpenChange={(o) => !o && setScanTarget(null)}
        title="Re-index already processed documents?"
        description="Choose whether to force re-processing of documents that haven't changed, or skip unchanged files."
        confirmLabel="Yes, force re-index"
        cancelLabel="No, skip unchanged"
        destructive
        onConfirm={() => {
          if (scanTarget) scanMutation.mutate({ sourceId: scanTarget, forceReprocess: true });
          setScanTarget(null);
        }}
        onCancel={() => {
          if (scanTarget) scanMutation.mutate({ sourceId: scanTarget, forceReprocess: false });
          setScanTarget(null);
        }}
      />

      {/* Delete confirm */}
      <ConfirmDialog
        open={deleteTarget !== null}
        onOpenChange={(o) => !o && setDeleteTarget(null)}
        title="Delete this source?"
        description="This removes the monitored source and all its indexed document parts. This action cannot be undone."
        confirmLabel="Delete"
        destructive
        onConfirm={() => {
          if (deleteTarget) deleteMutation.mutate(deleteTarget);
          setDeleteTarget(null);
        }}
      />
    </div>
  );
}
