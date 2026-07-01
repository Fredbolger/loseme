import { cn } from '@/lib/cn';

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  dot?: string; // hex/css color for an optional status dot
  variant?: 'neutral' | 'outline';
}

export function Badge({ className, dot, variant = 'neutral', children, ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 font-mono text-[11px] font-medium',
        variant === 'neutral' && 'bg-bg-tertiary text-text-secondary',
        variant === 'outline' && 'border border-border text-text-tertiary',
        className,
      )}
      {...props}
    >
      {dot && <span className="h-1.5 w-1.5 rounded-full" style={{ background: dot }} />}
      {children}
    </span>
  );
}
