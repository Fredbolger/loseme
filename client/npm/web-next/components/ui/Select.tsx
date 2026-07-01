import { cn } from '@/lib/cn';

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {}

export function Select({ className, ...props }: SelectProps) {
  return (
    <select
      className={cn(
        'h-8 rounded-md border border-border bg-bg-tertiary px-2.5 text-[12px] text-text-secondary outline-none transition-colors focus:border-accent-primary',
        className,
      )}
      {...props}
    />
  );
}

export function TextInput({ className, ...props }: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        'h-8 rounded-md border border-border bg-bg-tertiary px-3 text-[12px] text-text-primary outline-none transition-colors placeholder:text-text-tertiary focus:border-accent-primary',
        className,
      )}
      {...props}
    />
  );
}
