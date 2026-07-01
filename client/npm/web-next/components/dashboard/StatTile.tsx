import { Card } from '@/components/ui/Card';

interface StatTileProps {
  label: string;
  value: string | number;
  icon: string;
}

/**
 * Deliberately uninflected: all four dashboard stats are peers (counts of
 * different entity types), so giving them different accent colors implied
 * a meaning that wasn't there in the legacy client. One consistent style
 * reads as "a dashboard," not "a rainbow."
 */
export function StatTile({ label, value, icon }: StatTileProps) {
  return (
    <Card className="flex items-start justify-between">
      <div className="flex flex-col gap-1.5">
        <div className="text-[11px] font-medium uppercase tracking-wide text-text-tertiary">
          {label}
        </div>
        <div className="font-display text-3xl font-bold tracking-tight text-text-primary">
          {value}
        </div>
      </div>
      <div className="text-xl opacity-50">{icon}</div>
    </Card>
  );
}
