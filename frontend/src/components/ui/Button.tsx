import { forwardRef } from 'react';
import type { ButtonHTMLAttributes } from 'react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

type Variant = 'primary' | 'soft' | 'success' | 'outline';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: Variant;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
    ({ className, variant = 'primary', ...props }, ref) => {
        const variants = {
            primary: 'bg-accent text-white hover:bg-blue-700',
            soft: 'bg-accent-soft text-accent hover:bg-blue-100',
            success: 'bg-success text-white hover:bg-green-700',
            outline: 'border border-border bg-white text-text hover:bg-field',
        };

        return (
            <button
                ref={ref}
                className={twMerge(
                    clsx(
                        'inline-flex items-center justify-center rounded-btn px-4 py-2 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none',
                        variants[variant],
                        className
                    )
                )}
                {...props}
            />
        );
    }
);
Button.displayName = 'Button';