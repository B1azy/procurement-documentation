import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Download, RotateCw, AlertCircle, Pencil } from 'lucide-react';
import toast from 'react-hot-toast';

import { Stepper } from '../components/features/Stepper';
import { Tabs } from '../components/ui/Tabs';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { api } from '../api/client';
import type { Specification } from '../types/tz';

const SECTION_TITLES: Record<string, string> = {
    work_items: '1. Перечень работ',
    materials: '2. Материалы и требования',
    acceptance: '3. Критерии приёмки',
    normative_references: '4. Нормативные ссылки',
};

export function TZView() {
    const { id } = useParams();
    const navigate = useNavigate();
    const queryClient = useQueryClient();

    const [activeTab, setActiveTab] = useState('tz');

    // Стейт для перегенерации
    const [regenSection, setRegenSection] = useState<string | null>(null);
    const [regenInstruction, setRegenInstruction] = useState('');

    // Стейт для ручного редактирования (в виде простого текста)
    const [editSection, setEditSection] = useState<string | null>(null);
    const [editText, setEditText] = useState('');

    const { data: spec, isLoading, isError } = useQuery<Specification>({
        queryKey: ['spec', id],
        queryFn: async () => {
            const res = await api.get(`/purchases/${id}/specifications/current`);
            return res.data;
        },
        retry: false, // Не спамить запросами, если ТЗ нет
    });

    const handleDownload = async () => {
        if (!spec) return;
        try {
            const response = await api.get(`/purchases/${id}/specifications/${spec.id}/download/`, {
                responseType: 'blob',
            });
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `specification_v${spec.version}.docx`);
            document.body.appendChild(link);
            link.click();
            link.remove();
        } catch (err) {
            toast.error('Ошибка при скачивании файла');
        }
    };

    const { mutate: regenerate, isPending: isRegenerating } = useMutation({
        mutationFn: async () => {
            await api.post(`/purchases/${id}/specifications/${spec?.id}/regenerate-section/`, {
                section: regenSection,
                instruction: regenInstruction,
            });
        },
        onSuccess: () => {
            toast.success('Раздел успешно перегенерирован');
            setRegenSection(null);
            setRegenInstruction('');
            queryClient.invalidateQueries({ queryKey: ['spec', id] });
        },
        onError: () => toast.error('Ошибка генерации. Попробуйте еще раз.'),
    });

    // Сохранение ручных правок
    const { mutate: saveManual, isPending: isSaving } = useMutation({
        mutationFn: async () => {
            if (!spec || !editSection) return;

            const lines = editText.split('\n').map(l => l.trim()).filter(Boolean);
            let newSectionData: any = null;

            // Преобразуем текст обратно в структуры данных бэкенда
            if (editSection === 'work_items') {
                newSectionData = lines.map((name, i) => ({ order: i + 1, name, description: null }));
            }
            else if (editSection === 'materials') {
                newSectionData = { entries: lines, notes: null };
            }
            else if (editSection === 'acceptance') {
                newSectionData = { procedure: null, criteria: lines.map(text => ({ text, measurable: true })) };
            }
            else if (editSection === 'normative_references') {
                newSectionData = lines.map(line => ({ code: line, title: 'См. нормативный документ', source: 'Ручной ввод', verified: false }));
            }

            const newContent = { ...spec.content, [editSection]: newSectionData };
            await api.patch(`/purchases/${id}/specifications/${spec.id}/`, newContent);
        },
        onSuccess: () => {
            toast.success('Изменения сохранены (создана новая версия)');
            setEditSection(null);
            setEditText('');
            queryClient.invalidateQueries({ queryKey: ['spec', id] });
        },
        onError: () => toast.error('Ошибка сохранения.'),
    });

    // Открытие модалки редактирования (подготавливаем текст)
    const openEditModal = (section: string) => {
        setEditSection(section);
        const data = (spec?.content as any)[section];
        let initialText = '';

        if (section === 'work_items') {
            initialText = data?.map((item: any) => item.name).join('\n') || '';
        } else if (section === 'materials') {
            initialText = data?.entries?.join('\n') || '';
        } else if (section === 'acceptance') {
            initialText = data?.criteria?.map((c: any) => c.text).join('\n') || '';
        } else if (section === 'normative_references') {
            initialText = data?.map((r: any) => `${r.code} ${r.title}`).join('\n') || '';
        }

        setEditText(initialText);
    };

    if (isLoading) return <div className="text-center py-20 text-muted">Загрузка документа...</div>;

    if (isError) {
        return (
            <div className="max-w-[900px] mx-auto text-center py-20">
                <h2 className="text-2xl font-bold mb-4">ТЗ ещё не сформировано</h2>
                <p className="text-muted mb-8">Похоже, документ не был создан. Вернитесь к вопросам и нажмите «Сформировать ТЗ».</p>
                <Button onClick={() => navigate(`/requests/${id}/clarify`)}>
                    Перейти к вопросам
                </Button>
            </div>
        );
    }

    if (!spec) return null;

    const { content } = spec;

    const SectionHeader = ({ title, sectionKey }: { title: string, sectionKey: string }) => (
        <div className="flex justify-between items-center mb-3">
            <h3 className="font-bold text-[16px]">{title}</h3>
            <div className="flex gap-3">
                <button onClick={() => openEditModal(sectionKey)} className="text-muted hover:text-text text-sm flex items-center gap-1 transition-colors">
                    <Pencil size={14} /> Редактировать
                </button>
                <button onClick={() => setRegenSection(sectionKey)} className="text-accent hover:text-blue-700 text-sm flex items-center gap-1 transition-colors">
                    <RotateCw size={14} /> Перегенерировать
                </button>
            </div>
        </div>
    );

    return (
        <div className="max-w-[1200px] mx-auto relative">
            <h1 className="text-page-title mb-8">Техническое задание</h1>
            <Stepper currentStep={3} />

            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-4">
                    <Tabs
                        tabs={[{ id: 'tz', label: 'ТЗ' }, { id: 'contractors', label: 'Подрядчики и КП' }, { id: 'docs', label: 'Конкурсная документация' }]}
                        activeTab={activeTab}
                        onChange={(tab) => {
                            setActiveTab(tab);
                            if (tab === 'contractors') navigate(`/requests/${id}/contractors`);
                            if (tab === 'docs') navigate(`/requests/${id}/documents`);
                        }}
                    />
                </div>
                <Button onClick={handleDownload} className="gap-2">
                    <Download size={16} /> Скачать DOCX
                </Button>
            </div>

            <div className="flex gap-8 items-start">
                <div className="flex-1 bg-white rounded-card border border-border p-8 shadow-sm">
                    <div className="mb-8 border-b border-border pb-6">
                        <div className="flex items-center gap-3 mb-2">
                            <h2 className="text-2xl font-bold">{content.general_info?.object_name || 'Техническое задание'}</h2>
                            <Badge variant="warning">Черновик v{spec.version}</Badge>
                        </div>
                        <p className="text-sm text-muted">
                            {content.general_info?.address} • срок до {content.deadlines?.end || 'не указан'}
                        </p>
                    </div>

                    <div className="space-y-10 text-[14px] leading-relaxed text-text">
                        <section>
                            <SectionHeader title={SECTION_TITLES.work_items} sectionKey="work_items" />
                            {content.work_items?.length > 0 ? (
                                <ul className="list-decimal pl-5 space-y-1.5">
                                    {content.work_items.map((item, i) => <li key={i}>{item.name}</li>)}
                                </ul>
                            ) : <p className="text-muted italic">Работы не указаны (требует проверки)</p>}
                        </section>

                        <section>
                            <SectionHeader title={SECTION_TITLES.materials} sectionKey="materials" />
                            {content.materials?.entries?.length > 0 ? (
                                <ul className="list-disc pl-5 space-y-1.5">
                                    {content.materials.entries.map((item, i) => <li key={i}>{item}</li>)}
                                </ul>
                            ) : <p className="text-muted italic">Материалы не указаны</p>}
                        </section>

                        <section>
                            <SectionHeader title={SECTION_TITLES.acceptance} sectionKey="acceptance" />
                            <ul className="list-disc pl-5 space-y-1.5">
                                {content.acceptance?.criteria?.map((c, i) => <li key={i}>{c.text}</li>)}
                            </ul>
                        </section>

                        <section>
                            <SectionHeader title={SECTION_TITLES.normative_references} sectionKey="normative_references" />
                            {content.normative_references?.length > 0 ? (
                                <ul className="space-y-2">
                                    {content.normative_references.map((ref, i) => (
                                        <li key={i} className="flex items-center gap-2 flex-wrap">
                                            <span className="font-medium">{ref.code}</span> «{ref.title}»
                                            <Badge variant={ref.verified ? "success" : "warning"}>{ref.verified ? "из базы" : "проверить"}</Badge>
                                        </li>
                                    ))}
                                </ul>
                            ) : <p className="text-muted italic">Ссылки не найдены</p>}
                        </section>
                    </div>
                </div>

                <div className="w-[320px] shrink-0 sticky top-8">
                    <div className="bg-white rounded-card border border-border p-6">
                        <h3 className="font-bold text-[16px] mb-4">Допущения и проверка</h3>
                        {content.assumptions?.length > 0 ? (
                            <ul className="space-y-4">
                                {content.assumptions.map((a, i) => (
                                    <li key={i} className="flex gap-3 text-sm">
                                        <div className="mt-1 shrink-0"><AlertCircle size={16} className="text-warning" /></div>
                                        <div>
                                            <p className="text-text mb-1 leading-snug">{a.text}</p>
                                            <p className="text-xs text-muted">{a.source === 'user_defined' ? 'Указано пользователем' : 'Оценка агента'}</p>
                                        </div>
                                    </li>
                                ))}
                            </ul>
                        ) : <p className="text-sm text-muted">Допущений нет</p>}
                    </div>
                </div>
            </div>

            {/* Модалка: Перегенерация */}
            <Modal isOpen={!!regenSection} onClose={() => { setRegenSection(null); setRegenInstruction(''); }} title="Перегенерировать раздел">
                <div className="space-y-4">
                    <p className="text-sm text-muted">Опишите, что именно нужно изменить в разделе <strong>{regenSection && SECTION_TITLES[regenSection]}</strong>.</p>
                    <textarea
                        className="w-full rounded-btn border border-border bg-field px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-accent resize-none h-24"
                        placeholder="Например: добавь требование об обязательном фотоотчете..."
                        value={regenInstruction} onChange={(e) => setRegenInstruction(e.target.value)}
                    />
                    <div className="flex justify-end gap-2 mt-4">
                        <Button variant="outline" onClick={() => setRegenSection(null)}>Отмена</Button>
                        <Button onClick={() => regenerate()} disabled={!regenInstruction.trim() || isRegenerating}>
                            {isRegenerating ? 'Генерация...' : 'Перегенерировать'}
                        </Button>
                    </div>
                </div>
            </Modal>

            {/* Модалка: Ручное редактирование (Простой текст) */}
            <Modal isOpen={!!editSection} onClose={() => { setEditSection(null); setEditText(''); }} title={`Редактирование: ${editSection && SECTION_TITLES[editSection]}`}>
                <div className="space-y-4">
                    <p className="text-sm text-muted">
                        Введите каждый пункт с новой строки.
                    </p>
                    <textarea
                        className="w-full rounded-btn border border-border bg-field px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-accent resize-y min-h-[200px]"
                        value={editText}
                        onChange={(e) => setEditText(e.target.value)}
                        placeholder="Пункт 1&#10;Пункт 2&#10;Пункт 3"
                    />
                    <div className="flex justify-end gap-2 mt-4">
                        <Button variant="outline" onClick={() => setEditSection(null)}>Отмена</Button>
                        <Button onClick={() => saveManual()} disabled={isSaving}>
                            {isSaving ? 'Сохранение...' : 'Сохранить'}
                        </Button>
                    </div>
                </div>
            </Modal>
        </div>
    );
}