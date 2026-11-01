import { clsx } from 'clsx';
import type { ReactNode } from 'react';

type BadgeVariant = 'success' | 'warning' | 'default' | 'accent';

export function Badge({ children, variant = 'default', className }: { children: ReactNode, variant?: BadgeVariant, className?: string }) {
    const variants = {
        success: "bg-success-soft text-success border-success-border",
        warning: "bg-warning-soft text-warning border-warning-soft",
        default: "bg-field text-muted border-border",
        accent: "bg-accent-soft text-accent border-accent-soft",
    };

    return (
        <span className={clsx("inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border", variants[variant], className)}>
            {children}
        </span>
    );
}