import { clsx } from 'clsx';

interface ChipProps {
    label: string;
    selected: boolean;
    onClick: () => void;
}

export function Chip({ label, selected, onClick }: ChipProps) {
    return (
        <button
            type="button"
            onClick={onClick}
            className={clsx(
                "px-4 py-2 rounded-full text-sm transition-colors border",
                selected
                    ? "bg-accent text-white border-accent"
                    : "bg-white text-text border-border hover:border-accent/50"
            )}
        >
            {label}
        </button>
    );
}