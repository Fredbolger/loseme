import { cn } from '@/lib/cn';

export function Card({
  className,
  interactive = false,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & { interactive?: boolean }) {
  return (
    <div
      className={cn(
        'rounded-xl border border-border bg-bg-secondary p-4 shadow-sm transition-all',
        interactive && 'cursor-pointer hover:-translate-y-px hover:border-border-strong hover:shadow-md',
        className,
      )}
      {...props}
    />
  );
}
