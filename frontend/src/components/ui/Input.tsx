import React from 'react';
import { cn } from '@/lib/utils';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, helperText, className = '', id, ...props }, ref) => {
    const inputId = id || label?.toLowerCase().replace(/\s+/g, '-');
    return (
      <div className="w-full">
        {label && (
          <label htmlFor={inputId} className="block text-sm font-medium text-foreground mb-1.5">
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={inputId}
          className={cn(
            'w-full rounded-xl border px-4 py-2.5 text-sm transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-offset-background bg-card text-foreground placeholder:text-muted-foreground disabled:opacity-50 disabled:cursor-not-allowed',
            error
              ? 'border-danger-400 focus:ring-danger-500/30 focus:border-danger-500'
              : 'border-border focus:ring-primary-500/30 focus:border-primary-500',
            className,
          )}
          {...props}
        />
        {error && <p className="mt-1.5 text-xs text-danger-600 dark:text-danger-400">{error}</p>}
        {helperText && !error && <p className="mt-1.5 text-xs text-muted-foreground">{helperText}</p>}
      </div>
    );
  }
);

Input.displayName = 'Input';

export default Input;
