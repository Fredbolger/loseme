import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import type { ChunkerStat } from '@/lib/types';

export function ChunkerCard({ stat, totalParts }: { stat: ChunkerStat; totalParts: number }) {
  const pct = totalParts > 0 ? (stat.document_part_count / totalParts) * 100 : 0;

  return (
    <Card className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <Badge>{stat.chunker_name ?? 'unknown'}</Badge>
        <Badge variant="outline">{stat.chunker_version ?? '—'}</Badge>
      </div>

      <div>
        <div className="text-[10px] uppercase tracking-wide text-text-tertiary">Document Parts</div>
        <div className="font-display text-2xl font-bold text-text-primary">
          {stat.document_part_count.toLocaleString()}
        </div>
      </div>

      <div className="flex items-center gap-2.5">
        <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-bg-tertiary">
          <div
            className="h-full rounded-full bg-gradient-to-r from-accent-primary to-accent-secondary"
            style={{ width: `${pct}%` }}
          />
        </div>
        <span className="w-10 text-right text-[11px] font-medium text-text-secondary">
          {pct.toFixed(1)}%
        </span>
      </div>
    </Card>
  );
}
