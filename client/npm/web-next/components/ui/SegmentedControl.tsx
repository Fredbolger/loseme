import { cn } from '@/lib/cn';

interface SegmentedControlProps<T extends string> {
  options: { value: T; label: string }[];
  value: T;
  onChange: (value: T) => void;
}

export function SegmentedControl<T extends string>({
  options,
  value,
  onChange,
}: SegmentedControlProps<T>) {
  return (
    <div className="inline-flex rounded-md border border-border bg-bg-tertiary p-0.5">
      {options.map((opt) => (
        <button
          key={opt.value}
          onClick={() => onChange(opt.value)}
          className={cn(
            'rounded-[5px] px-3 py-1 text-[12px] font-medium transition-colors',
            value === opt.value
              ? 'bg-accent-primary text-white shadow-sm'
              : 'text-text-tertiary hover:text-text-primary',
          )}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
