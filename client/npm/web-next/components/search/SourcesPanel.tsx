'use client';

import { X, FileText } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { EmptyState } from '@/components/ui/States';
import { cn } from '@/lib/cn';
import type { SourceRef } from '@/lib/types';

interface SourcesPanelProps {
  open: boolean;
  sources: SourceRef[];
  onClose: () => void;
  onSelect: (source: SourceRef) => void;
}

export function SourcesPanel({ open, sources, onClose, onSelect }: SourcesPanelProps) {
  const sorted = [...sources].sort((a, b) => (b.score || 0) - (a.score || 0));

  return (
    <div
      className={cn(
        'fixed inset-y-0 right-0 z-[90] flex w-[320px] flex-col border-l border-border bg-bg-secondary shadow-xl transition-transform duration-500 ease-[cubic-bezier(0.34,1.56,0.64,1)]',
        open ? 'translate-x-0' : 'translate-x-full',
      )}
      style={{ top: 52 }}
    >
      <div className="flex items-center justify-between border-b border-border px-5 py-3.5">
        <h3 className="text-[14px] font-semibold text-text-primary">📄 Sources</h3>
        <Button variant="ghost" size="icon" onClick={onClose}>
          <X size={16} />
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto p-3">
        {!sorted.length ? (
          <EmptyState title="No sources available" />
        ) : (
          <div className="flex flex-col gap-2">
            {sorted.map((source, i) => {
              const name = (source.source_path || source.document_part_id).split(/[/\\]/).pop();
              return (
                <button
                  key={`${source.document_part_id}-${i}`}
                  onClick={() => onSelect(source)}
                  className="flex flex-col gap-1.5 rounded-lg border border-border bg-bg-tertiary p-3 text-left transition-colors hover:border-accent-primary hover:bg-bg-hover"
                >
                  <div className="flex items-center gap-2">
                    <FileText size={13} className="flex-shrink-0 text-text-tertiary" />
                    <span className="truncate text-[12.5px] font-medium text-text-primary">{name}</span>
                  </div>
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="text-status-success">
                      {((source.score || 0) * 100).toFixed(0)}% match
                    </span>
                    <span className="text-accent-primary">
                      {source.chunk_count || 1} section{(source.chunk_count || 1) > 1 ? 's' : ''}
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
