import React from 'react';
import { cn } from '@/lib/utils';

type BadgeVariant = 'default' | 'success' | 'warning' | 'danger' | 'info' | 'outline';

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  className?: string;
  dot?: boolean;
}

const variantClasses: Record<BadgeVariant, string> = {
  default: 'bg-clinical-100 text-clinical-700 dark:bg-clinical-800 dark:text-clinical-300',
  success: 'bg-secondary-50 text-secondary-700 dark:bg-secondary-900/30 dark:text-secondary-400 border border-secondary-200/50 dark:border-secondary-800/50',
  warning: 'bg-warning-50 text-warning-700 dark:bg-warning-900/30 dark:text-warning-400 border border-warning-200/50 dark:border-warning-800/50',
  danger: 'bg-danger-50 text-danger-700 dark:bg-danger-900/30 dark:text-danger-400 border border-danger-200/50 dark:border-danger-800/50',
  info: 'bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400 border border-primary-200/50 dark:border-primary-800/50',
  outline: 'border border-border text-muted-foreground',
};

const dotColors: Record<BadgeVariant, string> = {
  default: 'bg-clinical-500',
  success: 'bg-secondary-500',
  warning: 'bg-warning-500',
  danger: 'bg-danger-500',
  info: 'bg-primary-500',
  outline: 'bg-muted-foreground',
};

export const Badge: React.FC<BadgeProps> = ({ children, variant = 'default', className = '', dot = false }) => (
  <span className={cn(
    'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold tracking-wide',
    variantClasses[variant],
    className,
  )}>
    {dot && <span className={cn('w-1.5 h-1.5 rounded-full', dotColors[variant])} />}
    {children}
  </span>
);

export default Badge;
