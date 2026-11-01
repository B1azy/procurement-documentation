import { clsx } from 'clsx';

interface Tab {
    id: string;
    label: string;
}

interface TabsProps {
    tabs: Tab[];
    activeTab: string;
    onChange: (id: string) => void;
}

export function Tabs({ tabs, activeTab, onChange }: TabsProps) {
    return (
        <div className="flex gap-6 border-b border-border mb-6">
            {tabs.map((tab) => (
                <button
                    key={tab.id}
                    onClick={() => onChange(tab.id)}
                    className={clsx(
                        "pb-3 text-[15px] font-medium transition-colors border-b-2 -mb-[1px]",
                        activeTab === tab.id
                            ? "border-accent text-accent"
                            : "border-transparent text-muted hover:text-text"
                    )}
                >
                    {tab.label}
                </button>
            ))}
        </div>
    );
}