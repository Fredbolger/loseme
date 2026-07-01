'use client';

import { useEffect, useState } from 'react';
import { FileText, Mail } from 'lucide-react';
import { useSources, useDocumentsBySource } from '@/hooks/useSources';
import { useDetailPanelStore } from '@/lib/detail-panel-store';
import { EmptyState, LoadingState, ErrorState } from '@/components/ui/States';
import { Badge } from '@/components/ui/Badge';
import { SOURCE_TYPE_COLOR } from '@/lib/status-colors';
import type { DocumentPart, MonitoredSource, SourceType } from '@/lib/types';
import { cn } from '@/lib/cn';

const SOURCE_ICON: Record<SourceType, React.ReactNode> = {
  filesystem: <FileText size={16} />,
  thunderbird: <Mail size={16} />,
};

function docIcon(contentType?: string) {
  if (!contentType) return <FileText size={15} />;
  if (contentType.includes('pdf')) return <FileText size={15} className="text-red-400" />;
  if (contentType.includes('email')) return <Mail size={15} className="text-accent-quaternary" />;
  return <FileText size={15} />;
}

export default function SourcesPage() {
  const sourcesQ = useSources();
  const [selectedSourceId, setSelectedSourceId] = useState<string | null>(null);
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const docsQ = useDocumentsBySource(selectedSourceId);
  const openDetail = useDetailPanelStore((s) => s.open);

  // Auto-select first source once loaded, mirroring legacy default behavior.
  useEffect(() => {
    if (!selectedSourceId && sourcesQ.data?.sources.length) {
      setSelectedSourceId(sourcesQ.data.sources[0]!.id);
    }
  }, [sourcesQ.data, selectedSourceId]);

  function handleSelectDoc(doc: DocumentPart) {
    setSelectedDocId(doc.document_part_id);
    const docs = (docsQ.data?.documents ?? []).map((d) => ({
      document_part_id: d.document_part_id,
      source_type: d.source_type,
      source_path: d.source_path,
    }));
    openDetail(doc.document_part_id, docs);
  }

  return (
    <div
      className="grid h-[calc(100vh-52px)] grid-cols-1 lg:grid-cols-[260px_1fr]"
      style={{ gridTemplateRows: '100%' }}
    >
      {/* Source list */}
      <aside className="flex flex-col overflow-hidden border-b border-border bg-bg-secondary lg:border-b-0 lg:border-r">
        <div className="flex items-center justify-between border-b border-border px-4 py-3.5">
          <h2 className="text-[13px] font-semibold text-text-primary">Sources</h2>
          {sourcesQ.data && (
            <Badge variant="outline">{sourcesQ.data.sources.length}</Badge>
          )}
        </div>
        <div className="flex-1 overflow-y-auto p-2">
          {sourcesQ.isLoading ? (
            <LoadingState />
          ) : sourcesQ.isError ? (
            <ErrorState message="Could not load sources." />
          ) : !sourcesQ.data?.sources.length ? (
            <EmptyState icon="📁" title="No sources found" />
          ) : (
            <div className="flex flex-col gap-1">
              {sourcesQ.data.sources.map((s) => (
                <SourceListItem
                  key={s.id}
                  source={s}
                  active={s.id === selectedSourceId}
                  onClick={() => {
                    setSelectedSourceId(s.id);
                    setSelectedDocId(null);
                  }}
                />
              ))}
            </div>
          )}
        </div>
      </aside>

      {/* Document list */}
      <main className="flex flex-col overflow-hidden">
        <div className="flex items-center justify-between border-b border-border bg-bg-secondary px-5 py-3.5">
          <h1 className="truncate text-[14px] font-semibold text-text-primary">
            {selectedSourceId
              ? sourcesQ.data?.sources.find((s) => s.id === selectedSourceId)?.locator ?? 'Source'
              : 'Select a source'}
          </h1>
          {docsQ.data && <Badge variant="outline">{docsQ.data.documents.length} documents</Badge>}
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          {!selectedSourceId ? (
            <EmptyState icon="👈" title="Select a source from the left" />
          ) : docsQ.isLoading ? (
            <LoadingState label="Loading documents…" />
          ) : docsQ.isError ? (
            <ErrorState message="Could not load documents." />
          ) : !docsQ.data?.documents.length ? (
            <EmptyState title="No documents in this source" />
          ) : (
            <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 xl:grid-cols-3">
              {docsQ.data.documents.map((doc) => (
                <DocumentListItem
                  key={doc.document_part_id}
                  doc={doc}
                  active={doc.document_part_id === selectedDocId}
                  onClick={() => handleSelectDoc(doc)}
                />
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

function SourceListItem({
  source,
  active,
  onClick,
}: {
  source: MonitoredSource;
  active: boolean;
  onClick: () => void;
}) {
  const color = SOURCE_TYPE_COLOR[source.source_type];
  return (
    <button
      onClick={onClick}
      className={cn(
        'flex items-center gap-2.5 rounded-md px-3 py-2.5 text-left transition-colors',
        active ? 'bg-bg-active' : 'hover:bg-bg-hover',
      )}
      style={active ? { boxShadow: `inset 2px 0 0 0 ${color}` } : undefined}
    >
      <div
        className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-md"
        style={{ background: 'var(--bg-tertiary)', color }}
      >
        {SOURCE_ICON[source.source_type]}
      </div>
      <div className="min-w-0 flex-1">
        <div className="truncate text-[12.5px] font-medium text-text-primary">
          {source.locator || source.id.slice(0, 8)}
        </div>
        <div className="truncate text-[11px] text-text-tertiary">
          {source.source_type} · {source.device_id || 'unknown'}
        </div>
      </div>
      <span
        className={cn('h-1.5 w-1.5 flex-shrink-0 rounded-full', source.enabled ? 'bg-status-success' : 'bg-text-tertiary')}
      />
    </button>
  );
}

function DocumentListItem({
  doc,
  active,
  onClick,
}: {
  doc: DocumentPart;
  active: boolean;
  onClick: () => void;
}) {
  const fileName = doc.source_path.split(/[/\\]/).pop() || 'Untitled';
  const chunkCount = doc.chunk_ids ? (JSON.parse(doc.chunk_ids) as string[]).length : 0;

  return (
    <button
      onClick={onClick}
      className={cn(
        'flex flex-col gap-2 rounded-lg border p-3 text-left transition-colors',
        active ? 'border-accent-primary bg-bg-active' : 'border-border bg-bg-secondary hover:bg-bg-hover',
      )}
    >
      <div className="flex items-center gap-2">
        {docIcon(doc.content_type)}
        <span className="truncate text-[12.5px] font-medium text-text-primary">{fileName}</span>
      </div>
      <div className="flex items-center justify-between text-[11px] text-text-tertiary">
        <span className="truncate">{doc.content_type || 'unknown'}</span>
        <Badge variant={chunkCount > 0 ? 'neutral' : 'outline'} className="flex-shrink-0">
          {chunkCount > 0 ? `${chunkCount} chunks` : 'not chunked'}
        </Badge>
      </div>
    </button>
  );
}
