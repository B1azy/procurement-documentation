import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { Link, useNavigate } from 'react-router-dom';
import { Field, Input } from '../components/ui/FormControls';
import { Button } from '../components/ui/Button';
import { api } from '../api/client';
import { useAuthStore } from '../store/authStore';

const loginSchema = z.object({
    email: z.string().email('Некорректный email'),
    password: z.string().min(1, 'Введите пароль'),
});

type LoginValues = z.infer<typeof loginSchema>;

export function Login() {
    const navigate = useNavigate();
    const loginStore = useAuthStore();
    const [error, setError] = useState('');

    const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<LoginValues>({
        resolver: zodResolver(loginSchema),
    });

    const onSubmit = async (data: LoginValues) => {
        setError('');
        try {

            // FastAPI OAuth2 требует form-data, а не JSON!
            const formData = new URLSearchParams();
            formData.append('username', data.email); // Бэкенд ждет username
            formData.append('password', data.password);

            const response = await api.post('/auth/login', formData, {
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            });
            const token = response.data.access_token;

            const userResponse = await api.get('/auth/me', {
                headers: { Authorization: `Bearer ${token}` }
            });

            loginStore.login(token, userResponse.data);
            navigate('/'); // Перекидываем на главную
        } catch (err: any) {
            if (err.response?.status === 401) {
                setError('Неверный email или пароль');
            } else {
                setError('Ошибка сервера. Попробуйте позже.');
            }
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-page p-4">
            <div className="w-full max-w-md bg-white rounded-card border border-border p-8">
                <div className="text-center mb-8">
                    <div className="inline-flex h-12 w-12 rounded-xl bg-accent items-center justify-center font-bold text-xl text-white mb-4">
                        AI
                    </div>
                    <h1 className="text-2xl font-bold text-text">Вход в систему</h1>
                    <p className="text-sm text-muted mt-2">Введите ваши данные для доступа</p>
                </div>

                <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                    <Field label="Email">
                        <Input {...register('email')} type="email" placeholder="name@company.ru" />
                        {errors.email && <span className="text-xs text-red-500">{errors.email.message}</span>}
                    </Field>

                    <Field label="Пароль">
                        <Input {...register('password')} type="password" placeholder="••••••••" />
                        {errors.password && <span className="text-xs text-red-500">{errors.password.message}</span>}
                    </Field>

                    {error && <div className="p-3 bg-red-50 text-red-600 text-sm rounded-lg border border-red-100">{error}</div>}

                    <Button type="submit" className="w-full mt-2" disabled={isSubmitting}>
                        {isSubmitting ? 'Вход...' : 'Войти'}
                    </Button>
                </form>

                <p className="text-center text-sm text-muted mt-6">
                    Нет аккаунта? <Link to="/register" className="text-accent hover:underline">Зарегистрироваться</Link>
                </p>
            </div>
        </div>
    );
}