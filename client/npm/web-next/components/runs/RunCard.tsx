import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { fmtDate } from '@/lib/format';
import { RUN_STATUS_COLOR, RUN_STATUS_LABEL, SOURCE_TYPE_COLOR } from '@/lib/status-colors';
import type { IndexingRunSummary } from '@/lib/types';
import { cn } from '@/lib/cn';

interface RunCardProps {
  run: IndexingRunSummary;
  onStop: () => void;
  onResume: () => void;
  onDelete: () => void;
  pending?: boolean;
}

export function RunCard({ run, onStop, onResume, onDelete, pending }: RunCardProps) {
  const color = RUN_STATUS_COLOR[run.status];
  const sourceColor = SOURCE_TYPE_COLOR[run.source_type];
  const canStop = run.status === 'running' || run.status === 'starting';
  const canResume = run.status === 'interrupted';
  const canDelete = !canStop;

  const disc = run.discovered_document_count ?? 0;
  const idx = run.indexed_document_count ?? 0;
  const pct = disc > 0 ? Math.min(100, (idx / disc) * 100) : 0;

  return (
    <Card className="flex flex-col gap-3.5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span
          className="truncate font-mono text-[12px] font-semibold text-text-primary"
          title={run.run_id}
        >
          {run.run_id.slice(0, 18)}…
        </span>
        <div className="ml-auto flex items-center gap-2">
          <span
            className="rounded-full px-2 py-0.5 font-mono text-[10px] uppercase tracking-wide"
            style={{ color: sourceColor, background: 'var(--bg-tertiary)' }}
          >
            {run.source_type}
          </span>
          <span
            className="inline-flex items-center gap-1.5 rounded-full border border-border bg-bg-tertiary px-2 py-0.5 text-[11px]"
            style={{ color }}
          >
            <span
              className={cn('h-1.5 w-1.5 rounded-full', run.status === 'running' && 'animate-pulse')}
              style={{ background: color }}
            />
            {RUN_STATUS_LABEL[run.status]}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="flex flex-col gap-1">
          <span className="text-[10px] uppercase tracking-wide text-text-tertiary">Discovered</span>
          <span className="font-display text-xl font-bold text-text-primary">{disc || '—'}</span>
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-[10px] uppercase tracking-wide text-text-tertiary">Indexed</span>
          <span className="font-display text-xl font-bold text-status-success">{idx || '—'}</span>
        </div>
      </div>

      {disc > 0 && (
        <div>
          <div className="mb-1 flex justify-between text-[11px] text-text-tertiary">
            <span>Progress</span>
            <span className="font-medium text-text-secondary">{pct.toFixed(0)}%</span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-bg-tertiary">
            <div
              className="h-full rounded-full bg-gradient-to-r from-accent-primary to-accent-secondary transition-all"
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>
      )}

      <div className="flex flex-wrap gap-3 text-[11px] text-text-tertiary">
        <span>Started {fmtDate(run.started_at)}</span>
        <span>Updated {fmtDate(run.updated_at)}</span>
      </div>

      <div className="flex gap-2 border-t border-border pt-3">
        {canStop && (
          <Button size="sm" variant="danger" onClick={onStop} disabled={pending} className="flex-1">
            ⏹ Stop
          </Button>
        )}
        {canResume && (
          <Button size="sm" variant="primary" onClick={onResume} disabled={pending} className="flex-1">
            ▶ Resume
          </Button>
        )}
        {canDelete && (
          <Button size="sm" variant="outline" onClick={onDelete} disabled={pending} className="flex-1">
            🗑 Delete
          </Button>
        )}
      </div>
    </Card>
  );
}
