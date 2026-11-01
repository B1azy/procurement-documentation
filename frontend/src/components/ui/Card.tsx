import type { HTMLAttributes, ReactNode } from 'react';
import { clsx } from 'clsx';

interface CardProps extends HTMLAttributes<HTMLDivElement> {
    children: ReactNode;
}

export function Card({ className, children, ...props }: CardProps) {
    return (
        <div className={clsx("bg-white rounded-card border border-border p-6", className)} {...props}>
            {children}
        </div>
    );
}