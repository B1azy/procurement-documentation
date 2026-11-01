import { clsx } from 'clsx';
import { Check } from 'lucide-react';

const STEPS = [
    'Описание',
    'Уточнения',
    'ТЗ',
    'Подрядчики и КП',
    'Документация',
];

export function Stepper({ currentStep }: { currentStep: number }) {
    return (
        <div className="flex items-center justify-between w-full mb-8 relative">
            {/* Линия соединяющая шаги */}
            <div className="absolute left-0 top-4 -translate-y-1/2 w-full h-[2px] bg-border -z-10" />

            {STEPS.map((step, index) => {
                const stepNumber = index + 1;
                const isActive = stepNumber === currentStep;
                const isPast = stepNumber < currentStep;

                return (
                    <div key={step} className="flex flex-col items-center gap-2 bg-page px-2">
                        <div
                            className={clsx(
                                'w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold border-2 transition-colors',
                                isActive && 'bg-accent border-accent text-white',
                                isPast && 'bg-accent-soft border-accent text-accent',
                                !isActive && !isPast && 'bg-white border-border text-muted'
                            )}
                        >
                            {isPast ? <Check size={16} /> : stepNumber}
                        </div>
                        <span
                            className={clsx(
                                'text-[13px] font-medium transition-colors',
                                isActive ? 'text-text' : 'text-muted'
                            )}
                        >
                            {step}
                        </span>
                    </div>
                );
            })}
        </div>
    );
}