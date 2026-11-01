import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { FileText, Clock, ArrowRight, FolderOpen } from 'lucide-react';
import { api } from '../api/client';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';

// Тип закупки из бэкенда
interface Purchase {
    id: string;
    title: string;
    description: string;
    status: string;
    created_at: string;
}

// Словарь для красивого отображения статусов
const STATUS_MAP: Record<string, { label: string; variant: 'default' | 'accent' | 'success' | 'warning' }> = {
    draft: { label: 'Черновик', variant: 'default' },
    questions_pending: { label: 'Ожидает ответов', variant: 'warning' },
    ready_for_spec: { label: 'Готов к ТЗ', variant: 'accent' },
    spec_drafted: { label: 'ТЗ готово', variant: 'success' },
    exported: { label: 'Экспортировано', variant: 'success' },
};

export function Projects() {
    const navigate = useNavigate();

    // Загружаем список закупок
    const { data: purchases, isLoading } = useQuery<Purchase[]>({
        queryKey: ['purchases'],
        queryFn: async () => {
            const res = await api.get('/purchases/');
            return res.data;
        },
    });

    // Определяем, куда вести пользователя при клике на проект
    const handleOpenProject = (purchase: Purchase) => {
        if (purchase.status === 'draft' || purchase.status === 'questions_pending') {
            navigate(`/requests/${purchase.id}/clarify`);
        } else {
            navigate(`/requests/${purchase.id}/tz`);
        }
    };

    if (isLoading) {
        return <div className="text-center py-20 text-muted">Загрузка проектов...</div>;
    }

    return (
        <div className="max-w-[1100px] mx-auto space-y-8">
            <div className="flex items-center justify-between">
                <h1 className="text-page-title">Мои проекты</h1>
                <Button onClick={() => navigate('/requests/new')}>Создать новый</Button>
            </div>

            {!purchases || purchases.length === 0 ? (
                // Пустое состояние (Empty State)
                <Card className="flex flex-col items-center justify-center py-20 text-center">
                    <div className="w-16 h-16 bg-accent-soft text-accent rounded-full flex items-center justify-center mb-4">
                        <FolderOpen size={32} />
                    </div>
                    <h2 className="text-xl font-bold mb-2">У вас пока нет проектов</h2>
                    <p className="text-muted mb-6 max-w-sm">
                        Создайте первый запрос, и ИИ-агент поможет вам подготовить техническое задание.
                    </p>
                    <Button onClick={() => navigate('/requests/new')}>Создать запрос</Button>
                </Card>
            ) : (
                // Сетка с карточками проектов
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {purchases.map((purchase) => {
                        const status = STATUS_MAP[purchase.status] || { label: purchase.status, variant: 'default' };

                        return (
                            <Card
                                key={purchase.id}
                                className="flex flex-col h-full hover:border-accent/40 transition-colors cursor-pointer group"
                                onClick={() => handleOpenProject(purchase)}
                            >
                                <div className="flex items-start justify-between mb-4">
                                    <div className="w-10 h-10 bg-field rounded-lg flex items-center justify-center text-muted group-hover:text-accent transition-colors">
                                        <FileText size={20} />
                                    </div>
                                    <Badge variant={status.variant as any}>{status.label}</Badge>
                                </div>

                                <h3 className="font-bold text-[16px] text-text mb-2 line-clamp-2">
                                    {purchase.title}
                                </h3>

                                <p className="text-sm text-muted line-clamp-2 mb-4 flex-1">
                                    {purchase.description || 'Описание отсутствует'}
                                </p>

                                <div className="flex items-center justify-between pt-4 border-t border-border mt-auto">
                                    <div className="flex items-center gap-1.5 text-xs text-muted">
                                        <Clock size={14} />
                                        {new Date(purchase.created_at).toLocaleDateString('ru-RU')}
                                    </div>
                                    <div className="text-accent text-sm font-medium flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                        Открыть <ArrowRight size={14} />
                                    </div>
                                </div>
                            </Card>
                        );
                    })}
                </div>
            )}
        </div>
    );
}