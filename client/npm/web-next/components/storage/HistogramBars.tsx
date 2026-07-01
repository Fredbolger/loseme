import type { HistogramBucket } from '@/lib/types';

export function HistogramBars({ buckets }: { buckets: HistogramBucket[] }) {
  if (!buckets.length) {
    return <div className="py-6 text-center text-[12px] text-text-tertiary">No data</div>;
  }
  const max = Math.max(...buckets.map((b) => b.count), 1);

  return (
    <div className="flex flex-col gap-2">
      {buckets.map((b) => (
        <div key={b.label} className="flex items-center gap-3 text-[12px]">
          <span className="w-20 flex-shrink-0 text-right font-mono text-text-tertiary">{b.label}</span>
          <div className="h-4 flex-1 overflow-hidden rounded bg-bg-tertiary">
            <div
              className="h-full rounded bg-accent-primary transition-all"
              style={{ width: `${(b.count / max) * 100}%` }}
            />
          </div>
          <span className="w-12 flex-shrink-0 font-mono text-text-tertiary">{b.count.toLocaleString()}</span>
        </div>
      ))}
    </div>
  );
}
