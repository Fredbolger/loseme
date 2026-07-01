import { forwardRef } from 'react';
import { cn } from '@/lib/cn';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'outline';
export type ButtonSize = 'sm' | 'md' | 'icon';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
}

const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  primary:
    'bg-accent-primary text-white hover:opacity-90 active:opacity-100 disabled:opacity-40',
  secondary:
    'bg-bg-tertiary text-text-secondary border border-border hover:bg-bg-hover hover:text-text-primary disabled:opacity-40',
  outline:
    'bg-transparent text-text-secondary border border-border hover:bg-bg-hover hover:text-text-primary disabled:opacity-40',
  ghost:
    'bg-transparent text-text-tertiary hover:bg-bg-hover hover:text-text-primary disabled:opacity-40',
  danger:
    'bg-red-700 text-white hover:opacity-90 active:opacity-100 disabled:opacity-40',
};

const SIZE_CLASSES: Record<ButtonSize, string> = {
  sm: 'h-7 px-3 text-xs',
  md: 'h-9 px-4 text-[13px]',
  icon: 'h-8 w-8 p-0 justify-center',
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'secondary', size = 'md', ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          'inline-flex items-center justify-center gap-1.5 rounded-md font-semibold transition-colors disabled:cursor-not-allowed',
          VARIANT_CLASSES[variant],
          SIZE_CLASSES[size],
          className,
        )}
        {...props}
      />
    );
  },
);
Button.displayName = 'Button';
