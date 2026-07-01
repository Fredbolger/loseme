import { cn } from '@/lib/cn';

export function EmptyState({
  icon,
  title,
  subtitle,
}: {
  icon?: string;
  title: string;
  subtitle?: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 px-6 py-16 text-center">
      {icon && <div className="text-4xl opacity-40">{icon}</div>}
      <div className="text-[14px] font-medium text-text-secondary">{title}</div>
      {subtitle && <div className="max-w-xs text-[12px] text-text-tertiary">{subtitle}</div>}
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 px-6 py-16 text-center text-status-error">
      <div className="text-2xl">⚠️</div>
      <div className="text-[13px]">{message}</div>
    </div>
  );
}

export function Spinner({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        'h-4 w-4 animate-spin rounded-full border-2 border-border-strong border-t-accent-primary',
        className,
      )}
    />
  );
}

export function LoadingState({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2.5 py-16 text-[13px] text-text-tertiary">
      <Spinner />
      {label}
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn('animate-pulse rounded-md bg-bg-tertiary', className)} />;
}
