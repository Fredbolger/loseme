'use client';

import { useState } from 'react';
import { ChevronRight } from 'lucide-react';
import type { SourceTreeNode } from '@/lib/source-tree';
import { countDocs, countLeaves } from '@/lib/source-tree';
import { fmtDate } from '@/lib/format';
import { SOURCE_TYPE_COLOR, SOURCE_TYPE_ICON } from '@/lib/status-colors';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/cn';

interface SourceTreeViewProps {
  nodes: SourceTreeNode[];
  depth?: number;
  onScan: (sourceId: string) => void;
  onDelete: (sourceId: string) => void;
}

export function SourceTreeView({ nodes, depth = 0, onScan, onDelete }: SourceTreeViewProps) {
  return (
    <div className="flex flex-col gap-2">
      {nodes.map((node, i) =>
        node.type === 'leaf' ? (
          <SourceLeaf key={node.source.id} node={node} depth={depth} onScan={onScan} onDelete={onDelete} />
        ) : (
          <SourceGroup
            key={i}
            label={node.label}
            children={node.children}
            depth={depth}
            onScan={onScan}
            onDelete={onDelete}
          />
        ),
      )}
    </div>
  );
}

function SourceLeaf({
  node,
  depth,
  onScan,
  onDelete,
}: {
  node: Extract<SourceTreeNode, { type: 'leaf' }>;
  depth: number;
  onScan: (id: string) => void;
  onDelete: (id: string) => void;
}) {
  const s = node.source;
  const color = SOURCE_TYPE_COLOR[s._type];

  return (
    <Card className="flex flex-col gap-3" style={{ marginLeft: depth * 20 }}>
      <div className="flex items-center justify-between">
        <Badge dot={color} className="capitalize text-text-primary">
          {SOURCE_TYPE_ICON[s._type]} {s._type}
        </Badge>
        <Badge variant="outline">
          {s._docCount} doc{s._docCount !== 1 ? 's' : ''}
        </Badge>
      </div>

      <div>
        <div className="break-words text-[13px] font-medium text-text-primary">{s._loc || '—'}</div>
        <div className="mt-1 flex flex-wrap gap-3 text-[11px] text-text-tertiary">
          <span className="font-mono">{s.id.slice(0, 12)}…</span>
          <span>📱 {s.device_id || '—'}</span>
        </div>
      </div>

      <div className="flex items-center justify-between border-t border-border pt-2.5">
        <div className="flex items-center gap-1.5 text-[12px] text-text-secondary">
          <span
            className={cn(
              'h-1.5 w-1.5 rounded-full',
              s.enabled !== false ? 'bg-status-success' : 'bg-text-tertiary',
            )}
          />
          {s.enabled !== false ? 'Active' : 'Disabled'}
        </div>
        {s.last_ingested_at && (
          <span className="text-[11px] text-text-tertiary">Last synced {fmtDate(s.last_ingested_at)}</span>
        )}
      </div>

      <div className="flex gap-2 border-t border-border pt-2.5">
        <Button size="sm" variant="outline" onClick={() => onScan(s.id)} className="flex-1">
          ↺ Scan
        </Button>
        <Button size="sm" variant="danger" onClick={() => onDelete(s.id)}>
          Delete
        </Button>
      </div>
    </Card>
  );
}

function SourceGroup({
  label,
  children,
  depth,
  onScan,
  onDelete,
}: {
  label: string;
  children: SourceTreeNode[];
  depth: number;
  onScan: (id: string) => void;
  onDelete: (id: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const leafCount = children.reduce((acc, c) => acc + countLeaves(c), 0);
  const docCount = children.reduce((acc, c) => acc + countDocs(c), 0);

  return (
    <div className="flex flex-col gap-2">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2.5 rounded-xl border border-border bg-bg-secondary p-4 text-left shadow-sm transition-colors hover:border-border-strong hover:bg-bg-hover"
        style={{ marginLeft: depth * 20 }}
      >
        <ChevronRight
          size={14}
          className={cn('flex-shrink-0 text-text-tertiary transition-transform', open && 'rotate-90')}
        />
        <Badge variant="outline">
          {leafCount} source{leafCount !== 1 ? 's' : ''}
        </Badge>
        <span className="ml-auto truncate font-mono text-[12px] text-text-secondary">{label}/</span>
        <Badge variant="outline">
          {docCount} doc{docCount !== 1 ? 's' : ''}
        </Badge>
      </button>

      {open && (
        <div className="border-l border-border pl-3" style={{ marginLeft: depth * 20 + 12 }}>
          <SourceTreeView nodes={children} depth={0} onScan={onScan} onDelete={onDelete} />
        </div>
      )}
    </div>
  );
}
