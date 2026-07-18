'use client';

import { useEffect, useState } from 'react';
import { X, ChevronLeft, ChevronRight, FileText, ChevronDown, ChevronUp } from 'lucide-react';
import { useDetailPanelStore } from '@/lib/detail-panel-store';
import { useDocumentChunks, useDocumentDetail } from '@/hooks/useSources';
import { DocumentPreview } from '@/components/previews/DocumentPreview';
import { Button } from '@/components/ui/Button';
import { LoadingState, EmptyState } from '@/components/ui/States';
import { cn } from '@/lib/cn';
import { TagEditor } from '@/components/shared/TagEditor';
import { DocumentLabelAssigner } from '@/components/labels/DocumentLabelAssigner';
import type { DocumentPart } from '@/lib/types';
import type { DetailDoc } from '@/lib/detail-panel-store';

/**
 * Rebuilt from client/web/static/views/search/detail-panel.js. Preserves the
 * key UX decision from that file: the chunks drawer is a flex SIBLING of the
 * detail panel (not an overlay), so opening it visually *pushes* the panel
 * left instead of covering the document — this was a deliberate fix made
 * in the legacy client and is worth keeping.
 *
 * Difference from the old version: state lives in Zustand (lib/detail-panel-store)
 * instead of module-level mutable DOM refs, so this component is now usable
 * from both the Sources browser and Search views without duplicating the
 * 400+ lines of imperative DOM manipulation the old file had.
 */
export function DetailPanel() {
  const { isOpen, docs, activeIndex, chunksOpen, close, navigate, toggleChunks } = useDetailPanelStore();
  const activeDoc = docs[activeIndex];
  const [mlLabelsOpen, setMlLabelsOpen] = useState(false);

  const chunksQuery = useDocumentChunks(activeDoc?.document_part_id ?? null, chunksOpen);
  
  // Fetch full document details to get scope_json for Paperless documents
  const { data: fullDocData, isLoading: isLoadingFullDoc } = useDocumentDetail(activeDoc?.document_part_id ?? null);
  const fullDoc = fullDocData?.document_part;

  useEffect(() => {
    function onKeydown(e: KeyboardEvent) {
      if (!isOpen) return;
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;

      if (e.key === 'Escape') {
        e.preventDefault();
        chunksOpen ? toggleChunks(false) : close();
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        navigate(-1);
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        navigate(1);
      }
    }
    document.addEventListener('keydown', onKeydown);
    return () => document.removeEventListener('keydown', onKeydown);
  }, [isOpen, chunksOpen, close, navigate, toggleChunks]);

  useEffect(() => {
    document.body.style.overflow = isOpen ? 'hidden' : '';
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  if (!isOpen || !activeDoc) return null;

  const fileName = activeDoc.source_path.split(/[/\\]/).pop() || activeDoc.document_part_id;
  const total = docs.length;
  
  // Extract connection_id for Paperless documents
  const getConnectionId = (doc: any): string | null => {
    if (!doc || doc.source_type !== 'paperless') return null;
    
    try {
      const scope = doc.scope_json ? JSON.parse(doc.scope_json) : null;
      return scope?.connection_id || null;
    } catch {
      return null;
    }
  };
  
  const connectionId = fullDoc ? getConnectionId(fullDoc) : getConnectionId(activeDoc);

  return (
    <>
      {/* Overlay — click outside to close */}
      <div className="fixed inset-0 z-[100] bg-black/45 backdrop-blur-sm" onClick={close} />

      {/* Sliding group: chunks drawer (left) + detail panel (right), edge-to-edge */}
      <div className="fixed inset-y-0 right-0 z-[101] flex items-stretch">
        {/* Chunks drawer */}
        <div
          className={cn(
            'flex h-full flex-col overflow-hidden border-l border-border bg-bg-secondary shadow-xl transition-[width] duration-300 ease-out',
            chunksOpen ? 'w-[380px] min-w-[380px]' : 'w-0 min-w-0',
          )}
        >
          <div className="flex min-w-[380px] items-center justify-between border-b border-border px-5 py-3.5">
            <h3 className="text-[14px] font-semibold text-text-primary">Chunks</h3>
            <Button variant="ghost" size="icon" onClick={() => toggleChunks(false)}>
              <X size={15} />
            </Button>
          </div>
          <div className="min-w-[380px] flex-1 overflow-y-auto p-4">
            {chunksQuery.isLoading ? (
              <LoadingState label="Loading chunks…" />
            ) : !chunksQuery.data?.chunks.length ? (
              <EmptyState title="No chunks found for this document" />
            ) : (
              <div className="flex flex-col gap-3">
                {chunksQuery.data.chunks.map((chunk, i) => (
                  <div key={chunk.id} className="rounded-lg border border-border bg-bg-tertiary">
                    <div className="flex items-center justify-between border-b border-border px-3 py-2">
                      <span className="text-[11px] font-bold text-accent-primary">Chunk #{i + 1}</span>
                      {typeof chunk.metadata?.char_len === 'number' && (
                        <span className="font-mono text-[10px] text-text-tertiary">
                          {chunk.metadata.char_len as number} chars
                        </span>
                      )}
                    </div>
                    <pre className="whitespace-pre-wrap break-words px-3 py-2.5 font-mono text-[12px] leading-relaxed text-text-primary">
                      {chunk.text || 'No content'}
                    </pre>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Detail panel */}
        <div className="flex h-full w-[min(50vw,800px)] min-w-[480px] flex-col border-l border-border bg-bg-secondary shadow-xl">
          <div className="flex items-center justify-between gap-4 border-b border-border px-5 py-3.5">
            <div className="flex min-w-0 flex-1 items-center gap-2.5">
              <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-md bg-bg-tertiary">
                <FileText size={16} />
              </div>
              <span className="truncate text-[15px] font-semibold text-text-primary">{fileName}</span>
            </div>
            <div className="flex flex-shrink-0 items-center gap-3">
              <label className="flex cursor-pointer items-center gap-2 select-none">
                <span className="text-[12px] font-medium text-text-secondary">Chunks</span>
                <button
                  role="switch"
                  aria-checked={chunksOpen}
                  onClick={() => toggleChunks()}
                  className={cn(
                    'relative h-5 w-9 rounded-full border border-border transition-colors',
                    chunksOpen ? 'bg-accent-primary' : 'bg-bg-tertiary',
                  )}
                >
                  <span
                    className={cn(
                      'absolute top-px left-0.5 h-4 w-4 rounded-full bg-white transition-transform',
                      chunksOpen ? 'translate-x-3.5' : 'translate-x-0',
                    )}
                  />
                </button>
              </label>
              <Button variant="ghost" size="icon" onClick={close}>
                <X size={16} />
              </Button>
            </div>
          </div>

          <div className="flex flex-wrap gap-5 border-b border-border bg-bg-tertiary px-5 py-2.5 text-[12px]">
            <MetaItem label="Path" value={activeDoc.source_path} />
            <MetaItem label="Type" value={activeDoc.source_type} />
            {activeDoc.source_type === 'paperless' && connectionId && (
              <div className="flex items-center gap-2">
                <span className="text-text-tertiary">Tags:</span>
                <TagEditor 
                  documentPart={fullDoc ? 
                    { document_part_id: fullDoc.document_part_id, source_type: fullDoc.source_type, scope_json: fullDoc.scope_json } :
                    { document_part_id: activeDoc.document_part_id, source_type: activeDoc.source_type, scope_json: activeDoc.scope_json }
                  } 
                  connectionId={connectionId}
                />
              </div>
            )}
          </div>
          
          {/* ML Labels section - separate from Paperless tags, available for all source types */}
          <div className="border-b border-border">
            <button
              onClick={() => setMlLabelsOpen(!mlLabelsOpen)}
              className="flex w-full items-center justify-between px-5 py-2 text-[12px] font-semibold text-text-secondary hover:bg-bg-tertiary transition-colors"
            >
              <span className="flex items-center gap-1.5">
                ML Labels
              </span>
              {mlLabelsOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </button>
            {mlLabelsOpen && (
              <div className="px-5 pb-3">
                <DocumentLabelAssigner documentPartId={activeDoc.document_part_id} />
              </div>
            )}
          </div>

          <div className="flex-1 overflow-hidden">
            <DocumentPreview docId={activeDoc.document_part_id} sourcePath={activeDoc.source_path} />
          </div>

          {total > 1 && (
            <div className="flex items-center justify-between border-t border-border px-5 py-3">
              <span className="font-mono text-[12px] text-text-tertiary">
                {activeIndex + 1} / {total}
              </span>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => navigate(-1)} disabled={activeIndex <= 0}>
                  <ChevronLeft size={14} /> Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => navigate(1)}
                  disabled={activeIndex >= total - 1}
                >
                  Next <ChevronRight size={14} />
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

function MetaItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="text-text-tertiary">{label}:</span>
      <span className="max-w-[280px] truncate font-mono text-[11px] text-text-primary">{value || '—'}</span>
    </div>
  );
}
