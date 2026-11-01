import { forwardRef } from 'react';
import type { InputHTMLAttributes, SelectHTMLAttributes, TextareaHTMLAttributes, ReactNode } from 'react';
import { clsx } from 'clsx';

// Обертка для полей (Label + Input)
export function Field({ label, children, className }: { label: string; children: ReactNode; className?: string }) {
    return (
        <div className={clsx("flex flex-col gap-1.5", className)}>
            <label className="text-[13px] font-medium text-text">{label}</label>
            {children}
        </div>
    );
}

// Базовые стили для инпутов
const baseInputStyles = "w-full rounded-btn border border-border bg-field px-4 py-2.5 text-sm text-text placeholder:text-placeholder focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent transition-all disabled:opacity-50";

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
    ({ className, ...props }, ref) => (
        <input ref={ref} className={clsx(baseInputStyles, className)} {...props} />
    )
);
Input.displayName = 'Input';

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(
    ({ className, ...props }, ref) => (
        <textarea ref={ref} className={clsx(baseInputStyles, "resize-none min-h-[100px]", className)} {...props} />
    )
);
Textarea.displayName = 'Textarea';

export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(
    ({ className, children, ...props }, ref) => (
        <select ref={ref} className={clsx(baseInputStyles, "appearance-none cursor-pointer", className)} {...props}>
            {children}
        </select>
    )
);
Select.displayName = 'Select';