import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/Button';
import { ArrowRight } from 'lucide-react';
import { useAuthStore } from '../store/authStore';

export function Home() {
    const navigate = useNavigate();
    const user = useAuthStore((state) => state.user);

    const firstName = user?.full_name?.split(' ')[0] || 'друг';

    return (
        <div className="space-y-8">
            {/* Приветствие */}
            <div className="bg-white rounded-card border border-border p-10 flex justify-between items-center relative overflow-hidden">
                <div className="max-w-lg relative z-10">
                    <h1 className="text-[40px] font-extrabold text-text leading-tight mb-3">
                        Привет, {firstName}!
                    </h1>
                    <p className="text-muted text-[15px] mb-8 leading-relaxed">
                        ИИ-агент поможет быстро подготовить техническое задание, собрать коммерческие предложения и оформить конкурс.
                    </p>
                    <Button onClick={() => navigate('/requests/new')} className="px-6 py-2.5">
                        Создать новый запрос <ArrowRight size={16} className="ml-2" />
                    </Button>
                </div>
                {/* Декоративная плашка */}
                <div className="absolute right-10 top-1/2 -translate-y-1/2 w-64 h-48 bg-accent-soft rounded-card opacity-50 flex flex-col p-6 gap-3">
                    <div className="h-4 w-1/2 bg-accent/20 rounded-full" />
                    <div className="h-4 w-3/4 bg-accent/20 rounded-full" />
                    <div className="mt-auto h-10 bg-white rounded-btn border border-border flex items-center px-4">
                        <div className="h-2 w-full bg-accent rounded-full" />
                    </div>
                </div>
            </div>

            {/* Как это работает */}
            <div>
                <h2 className="text-xl font-bold mb-4">Как это работает?</h2>
                <div className="grid grid-cols-3 gap-6">
                    {[
                        { n: 1, title: 'Введите данные', desc: 'Загрузите фото дефекта, опишите задачу и заполните поля.' },
                        { n: 2, title: 'Агент уточняет и пишет ТЗ', desc: 'Задаёт вопросы простым языком, формирует ТЗ с допущениями.' },
                        { n: 3, title: 'Получите пакет документов', desc: 'ТЗ, КП, НМЦ и конкурсная документация — файлами.' },
                    ].map((step) => (
                        <div key={step.n} className="bg-white rounded-card border border-border p-6">
                            <div className="w-10 h-10 rounded-lg bg-accent-soft text-accent flex items-center justify-center font-bold text-lg mb-4">
                                {step.n}
                            </div>
                            <h3 className="font-bold text-[15px] mb-2">{step.title}</h3>
                            <p className="text-sm text-muted leading-relaxed">{step.desc}</p>
                        </div>
                    ))}
                </div>
            </div>

            {/* Преимущества */}
            <div className="grid grid-cols-3 gap-6">
                {[
                    { title: 'Экономия времени', desc: 'С нескольких дней до минут' },
                    { title: 'Прозрачная закупка', desc: 'Не менее 3 КП и расчёт НМЦ' },
                    { title: 'Меньше рисков', desc: 'Цена и работы обоснованы' },
                ].map((adv) => (
                    <div key={adv.title} className="bg-white rounded-card border border-border p-6">
                        <h3 className="font-bold text-[15px] mb-1">{adv.title}</h3>
                        <p className="text-sm text-muted">{adv.desc}</p>
                    </div>
                ))}
            </div>
        </div>
    );
}