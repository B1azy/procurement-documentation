import { useState } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { useNavigate } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import toast from 'react-hot-toast';

import { Stepper } from '../components/features/Stepper';
import { Dropzone } from '../components/ui/Dropzone';
import { Field, Input, Select, Textarea } from '../components/ui/FormControls';
import { Button } from '../components/ui/Button';
import { api } from '../api/client';

const requestSchema = z.object({
    description: z.string().optional(),
    address: z.string().optional(),
    workType: z.string().optional(),
    customWorkType: z.string().optional(), // Для ручного ввода
    deadline: z.string().optional(),
    customDeadline: z.string().optional(), // Для ручного ввода
    budget: z.string().optional(),
    contractorReq: z.string().optional(),
    hasPersonalData: z.boolean(),
});

type RequestFormValues = z.infer<typeof requestSchema>;

export function NewRequest() {
    const navigate = useNavigate();
    const [files, setFiles] = useState<File[]>([]);

    const { register, handleSubmit, formState: { errors, isSubmitting }, control, setError, watch } = useForm<RequestFormValues>({
        resolver: zodResolver(requestSchema),
        defaultValues: { hasPersonalData: false, workType: '', deadline: '' }
    });

    // Следим за выбором, чтобы показать поле для ручного ввода
    const selectedWorkType = watch('workType');
    const selectedDeadline = watch('deadline');

    const onSubmit = async (data: RequestFormValues) => {
        if (!data.description && files.length === 0) {
            setError('description', { type: 'manual', message: 'Заполните описание или прикрепите фото' });
            return;
        }

        try {
            const title = data.description ? data.description.slice(0, 50) : 'Запрос по фото';

            // Если выбрано "Другое", берем текст из ручного ввода
            const finalWorkType = data.workType === 'other' ? data.customWorkType : data.workType;
            const finalDeadline = data.deadline === 'custom' ? data.customDeadline : data.deadline;

            const response = await api.post('/purchases/', {
                title,
                description: data.description || '',
                structured_fields: {
                    address: data.address,
                    work_type: finalWorkType || undefined,
                    desired_dates: finalDeadline || undefined,
                    constraints: data.contractorReq,
                    budget: data.budget,
                }
            });

            toast.success('Запрос создан! Переходим к уточнениям...');
            navigate(`/requests/${response.data.id}/clarify`);
        } catch (err) {
            toast.error('Ошибка при создании запроса.');
            console.error(err);
        }
    };

    return (
        <div className="max-w-[900px] mx-auto">
            <h1 className="text-page-title mb-8">Новый запрос</h1>
            <Stepper currentStep={1} />

            <form onSubmit={handleSubmit(onSubmit)} className="bg-white rounded-card border border-border p-8 space-y-8">
                <div>
                    <h2 className="text-card-title mb-4">Опишите вашу задачу</h2>
                    <Dropzone files={files} onChange={setFiles} />
                </div>

                <Field label="Краткое описание проблемы" className="max-w-full">
                    <Textarea
                        {...register('description')}
                        placeholder="Например: требуется ремонт мягкой кровли, образовалась протечка..."
                        className={errors.description ? "border-red-500 focus:ring-red-500" : ""}
                    />
                    {errors.description && <span className="text-xs text-red-500">{errors.description.message}</span>}
                </Field>

                <div>
                    <h3 className="font-bold text-text mb-4">Параметры <span className="font-normal text-muted text-sm">(все необязательные)</span></h3>

                    <div className="space-y-4">
                        <Field label="Адрес объекта">
                            <Input {...register('address')} placeholder="Город, улица, дом" />
                        </Field>

                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Field label="Вид работ">
                                    <Select {...register('workType')}>
                                        <option value="">Выберите значение</option>
                                        <option value="facade">Фасад</option>
                                        <option value="tile">Плитка</option>
                                        <option value="door">Доводчик</option>
                                        <option value="leak">Протечка</option>
                                        <option value="window">Замена окна</option>
                                        <option value="roof">Ремонт кровли</option>
                                        <option value="other">Другое (ввести вручную)</option>
                                    </Select>
                                </Field>
                                {selectedWorkType === 'other' && (
                                    <Input {...register('customWorkType')} placeholder="Введите вид работ..." autoFocus />
                                )}
                            </div>

                            <div className="space-y-2">
                                <Field label="Сроки выполнения">
                                    <Select {...register('deadline')}>
                                        <option value="">Выберите срок</option>
                                        <option value="urgent">Срочно (до 3 дней)</option>
                                        <option value="week">В течение недели</option>
                                        <option value="month">В течение месяца</option>
                                        <option value="custom">Другое (ввести вручную)</option>
                                    </Select>
                                </Field>
                                {selectedDeadline === 'custom' && (
                                    <Input {...register('customDeadline')} placeholder="Например: до 15 ноября..." autoFocus />
                                )}
                            </div>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <Field label="Бюджет, если есть">
                                <Input {...register('budget')} placeholder="до 500 000 ₽" />
                            </Field>
                            <Field label="Требования к подрядчику">
                                <Input {...register('contractorReq')} placeholder="Допуск СРО, опыт от 3 лет" />
                            </Field>
                        </div>
                    </div>
                </div>

                <div className="flex items-center justify-between pt-6 border-t border-border">
                    <label className="flex items-center gap-2 cursor-pointer">
                        <Controller
                            name="hasPersonalData"
                            control={control}
                            render={({ field }) => (
                                <input
                                    type="checkbox"
                                    className="w-4 h-4 rounded border-border text-accent focus:ring-accent"
                                    checked={field.value}
                                    onChange={field.onChange}
                                />
                            )}
                        />
                        <span className="text-sm text-text">В описании или на фото есть персональные данные</span>
                    </label>

                    <Button type="submit" className="px-8" disabled={isSubmitting}>
                        {isSubmitting ? 'Создание...' : 'Далее'}
                        {!isSubmitting && <ArrowRight size={16} className="ml-2" />}
                    </Button>
                </div>
            </form>
        </div>
    );
}