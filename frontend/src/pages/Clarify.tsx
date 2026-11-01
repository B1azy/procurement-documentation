import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { ArrowRight, Info } from 'lucide-react';
import { Stepper } from '../components/features/Stepper';
import { Card } from '../components/ui/Card';
import { Chip } from '../components/ui/Chip';
import { Button } from '../components/ui/Button';
import { api } from '../api/client';
import { Field, Input } from '../components/ui/FormControls';
import toast from 'react-hot-toast';

// Типы (соответствуют схемам бэкенда)
interface Question {
    id: string;
    text: string;
    hint: string | null;
    options: string[];
    answer: string | null;
    answer_source: string | null;
}

interface PurchaseData {
    id: string;
    title: string;
    description: string;
    structured_fields: any;
}

export function Clarify() {
    const { id } = useParams();
    const navigate = useNavigate();

    // Стейт для ответов: { [questionId]: string | boolean }
    const [answers, setAnswers] = useState<Record<string, string | boolean>>({});

    // 1. Загружаем данные закупки
    const { data: purchase, isLoading: isLoadingPurchase } = useQuery<PurchaseData>({
        queryKey: ['purchase', id],
        queryFn: async () => {
            const res = await api.get(`/purchases/${id}/`);
            return res.data;
        },
        enabled: !!id,
    });

    // 2. Загружаем вопросы (и генерируем их, если пусто)
    const { data: questions, isLoading: isLoadingQuestions } = useQuery<Question[]>({
        queryKey: ['questions', id],
        queryFn: async () => {
            // Проверяем, есть ли уже вопросы
            const existing = await api.get(`/purchases/${id}/questions/`);
            if (existing.data.length > 0) return existing.data;

            // Если нет — генерируем
            const generated = await api.post(`/purchases/${id}/questions/generate/`);
            return generated.data;
        },
        enabled: !!id,
        retry: false, // Чтобы не спамить, если бэкенд упал
    });

    useEffect(() => {
        if (questions && questions.length > 0) {
            const savedAnswers: Record<string, string | boolean> = {};

            questions.forEach((q) => {
                if (q.answer_source === 'dont_know') {
                    savedAnswers[q.id] = true; // Это выбранный чип "Не знаю"
                } else if (q.answer_source === 'user_defined' && q.answer) {
                    savedAnswers[q.id] = q.answer; // Это текст или выбранный чип
                }
            });

            // Обновляем стейт, если нашли сохраненные ответы
            if (Object.keys(savedAnswers).length > 0) {
                setAnswers(savedAnswers);
            }
        }
    }, [questions]);

    // Обработка выбора ответа
    const handleSelect = (questionId: string, value: string | boolean) => {
        setAnswers(prev => ({ ...prev, [questionId]: value }));
    };

    // 3. Мутация отправки ответов и генерации ТЗ
    const { mutate: submitAnswers, isPending: isSubmitting } = useMutation({
        mutationFn: async () => {
            const batchAnswers = Object.entries(answers).map(([qId, answer]) => {
                if (answer === true) return { question_id: qId, dont_know: true };
                return { question_id: qId, answer: answer as string };
            });

            try {
                // Пытаемся отправить ответы
                await api.post(`/purchases/${id}/questions/answer-batch/`, { answers: batchAnswers });
            } catch (err: any) {
                // Если 409 — значит ответы УЖЕ сохранены (например, при повторном клике), игнорируем
                if (err.response?.status !== 409) throw err;
            }

            // Просим сгенерировать ТЗ
            await api.post(`/purchases/${id}/specifications/generate/`);
        },
        onSuccess: () => {
            toast.success('ТЗ успешно сформировано!');
            navigate(`/requests/${id}/tz`);
        },
        onError: (err: any) => {
            console.error(err);
            // Показываем ту самую ошибку 502 от бэкенда
            const errorMsg = err.response?.data?.detail
                ? (typeof err.response.data.detail === 'string' ? err.response.data.detail : 'Ошибка валидации')
                : 'Ошибка сервера. Попробуйте еще раз.';

            toast.error(errorMsg, { duration: 6000 });
        }
    });

    // Мутация для генерации ТЗ, если вопросов не было
    const { mutate: generateWithoutQuestions, isPending: isGeneratingWithoutQuestions } = useMutation({
        mutationFn: async () => {
            // Добавил слэш в конце, чтобы избежать 307 редиректа
            await api.post(`/purchases/${id}/specifications/generate/`);
        },
        onSuccess: () => {
            toast.success('ТЗ успешно сформировано!');
            navigate(`/requests/${id}/tz`);
        },
        onError: (err: any) => {
            const errorMsg = err.response?.data?.detail || 'Ошибка генерации ТЗ. Попробуйте позже.';
            toast.error(errorMsg, { duration: 6000 });
        }
    });

    const allAnswered = questions?.every(q => {
        const ans = answers[q.id];
        return ans !== undefined && ans !== '';
    });

    if (isLoadingPurchase || isLoadingQuestions) {
        return (
            <div className="max-w-[1200px] mx-auto py-20 text-center text-muted">
                <div className="animate-pulse flex flex-col items-center">
                    <div className="w-12 h-12 rounded-full border-4 border-accent border-t-transparent animate-spin mb-4" />
                    <p>Агент анализирует закупку и готовит вопросы...</p>
                </div>
            </div>
        );
    }

    // Если вопросов нет (бэкенд сказал, что данные полные)
    if (questions?.length === 0) {
        return (
            <div className="max-w-[900px] mx-auto">
                <Stepper currentStep={2} />
                <Card className="text-center py-12 flex flex-col items-center">
                    <h2 className="text-xl font-bold mb-2">Данных достаточно!</h2>
                    <p className="text-muted mb-6 max-w-md">Агент не нашёл пробелов. Вы можете сразу перейти к формированию ТЗ.</p>
                    <Button
                        onClick={() => generateWithoutQuestions()}
                        disabled={isGeneratingWithoutQuestions}
                        className="px-8"
                    >
                        {isGeneratingWithoutQuestions ? 'Формируем ТЗ...' : 'Сформировать ТЗ'}
                    </Button>
                </Card>
            </div>
        );
    }

    return (
        <div className="max-w-[1200px] mx-auto">
            <h1 className="text-page-title mb-8">Уточняющие вопросы</h1>
            <Stepper currentStep={2} />

            <div className="flex gap-8 items-start">
                {/* Левая колонка: Вопросы */}
                <div className="flex-1 space-y-4">
                    {/* Карточка фото-гипотезы (Пока условная) */}
                    <Card className="flex gap-4 items-center bg-field">
                        <div className="w-16 h-16 bg-white rounded-lg border border-border flex items-center justify-center text-muted text-xs">
                            Фото
                        </div>
                        <div>
                            <p className="text-xs text-muted mb-1">Агент распознал по фото</p>
                            <p className="font-bold text-text mb-2">Повреждение фасада (требует уточнения)</p>
                            <div className="flex gap-2">
                                <Button variant="soft" className="py-1 px-3 text-xs">Верно</Button>
                                <Button variant="outline" className="py-1 px-3 text-xs">Исправить</Button>
                            </div>
                        </div>
                    </Card>

                    {questions?.map((q, index) => {
                        const currentAnswer = answers[q.id];
                        // Проверяем, является ли ответ кастомным (введенным вручную)
                        const isCustom = typeof currentAnswer === 'string' && !q.options.includes(currentAnswer);

                        return (
                            <Card key={q.id}>
                                <h3 className="font-bold text-[15px] mb-1">{index + 1}. {q.text}</h3>
                                {q.hint && (
                                    <p className="text-sm text-muted mb-4 flex items-center gap-1.5">
                                        <Info size={14} /> {q.hint}
                                    </p>
                                )}

                                {/* Чипы с готовыми вариантами */}
                                <div className="flex flex-wrap gap-2 mb-4">
                                    {q.options.map((opt) => (
                                        <Chip
                                            key={opt}
                                            label={opt}
                                            selected={currentAnswer === opt}
                                            onClick={() => handleSelect(q.id, opt)}
                                        />
                                    ))}
                                    {/* Всегда добавляем "Не знаю" */}
                                    <Chip
                                        label="Не знаю"
                                        selected={currentAnswer === true}
                                        onClick={() => handleSelect(q.id, true)}
                                    />
                                </div>

                                {/* Поле для своего варианта */}
                                <Input
                                    placeholder="Или введите свой вариант ответа..."
                                    value={isCustom ? (currentAnswer as string) : ''}
                                    onChange={(e) => handleSelect(q.id, e.target.value)}
                                    className="bg-white"
                                />
                            </Card>
                        );
                    })}
                </div>

                {/* Правая колонка: Сводка */}
                <div className="w-[320px] space-y-4 sticky top-8">
                    <Card>
                        <h3 className="font-bold mb-4">Что агент уже понял</h3>
                        <ul className="space-y-3 text-sm">
                            <li><span className="text-muted">Адрес:</span> {purchase?.structured_fields?.address || 'не указан'}</li>
                            <li><span className="text-muted">Вид работ:</span> {purchase?.structured_fields?.work_type || 'не указан'}</li>
                            <li><span className="text-muted">Срок:</span> {purchase?.structured_fields?.desired_dates || 'не указан'}</li>
                            <li><span className="text-muted">Бюджет:</span> {purchase?.structured_fields?.budget || 'не указан'}</li>
                        </ul>
                    </Card>

                    <Card>
                        <div className="flex justify-between items-end mb-2">
                            <h3 className="font-bold">Раунд вопросов 1 из 3</h3>
                        </div>
                        <div className="w-full h-1.5 bg-border rounded-full mb-4 overflow-hidden">
                            <div className="h-full bg-accent w-1/3" />
                        </div>
                        <p className="text-xs text-muted">
                            «Не знаю» — не проблема: агент подставит типовое значение и отметит как допущение.
                        </p>
                    </Card>

                    <Button
                        className="w-full py-3"
                        disabled={!allAnswered || isSubmitting}
                        onClick={() => submitAnswers()}
                    >
                        {isSubmitting ? 'Формируем ТЗ...' : 'Сформировать ТЗ'}
                        {!isSubmitting && <ArrowRight size={16} className="ml-2" />}
                    </Button>
                </div>
            </div>
        </div>
    );
}