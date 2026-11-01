import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { Link, useNavigate } from 'react-router-dom';
import { Field, Input } from '../components/ui/FormControls';
import { Button } from '../components/ui/Button';
import { api } from '../api/client';
import { useAuthStore } from '../store/authStore';

const registerSchema = z.object({
    full_name: z.string().min(2, 'Минимум 2 символа'),
    email: z.string().email('Некорректный email'),
    password: z.string().min(8, 'Пароль должен быть от 8 символов'),
    confirmPassword: z.string()
}).refine((data) => data.password === data.confirmPassword, {
    message: "Пароли не совпадают",
    path: ["confirmPassword"],
});

type RegisterValues = z.infer<typeof registerSchema>;

export function Register() {
    const navigate = useNavigate();
    const loginStore = useAuthStore();
    const [error, setError] = useState('');

    const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<RegisterValues>({
        resolver: zodResolver(registerSchema),
    });

    const onSubmit = async (data: RegisterValues) => {
        setError('');
        try {
            // 1. Создаем пользователя
            await api.post('/auth/register', {
                full_name: data.full_name,
                email: data.email,
                password: data.password
            });

            // 2. Сразу логиним его (отправляем form-data)
            const formData = new URLSearchParams();
            formData.append('username', data.email);
            formData.append('password', data.password);

            const loginResponse = await api.post('/auth/login', formData, {
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            });
            const token = loginResponse.data.access_token;

            // Получаем данные профиля (чтобы достать full_name)
            const userResponse = await api.get('/auth/me', {
                headers: { Authorization: `Bearer ${token}` }
            });

            loginStore.login(token, userResponse.data);
            navigate('/');
        } catch (err: any) {
            if (err.response?.status === 409) {
                setError('Пользователь с таким email уже существует');
            } else {
                setError('Ошибка при регистрации. Проверьте данные.');
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
                    <h1 className="text-2xl font-bold text-text">Создать аккаунт</h1>
                </div>

                <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                    <Field label="Имя и фамилия">
                        <Input {...register('full_name')} placeholder="Иван Иванов" />
                        {errors.full_name && <span className="text-xs text-red-500">{errors.full_name.message}</span>}
                    </Field>
                    <Field label="Email">
                        <Input {...register('email')} type="email" placeholder="name@company.ru" />
                        {errors.email && <span className="text-xs text-red-500">{errors.email.message}</span>}
                    </Field>

                    <Field label="Пароль">
                        <Input {...register('password')} type="password" placeholder="Минимум 8 символов" />
                        {errors.password && <span className="text-xs text-red-500">{errors.password.message}</span>}
                    </Field>

                    <Field label="Подтвердите пароль">
                        <Input {...register('confirmPassword')} type="password" placeholder="Повторите пароль" />
                        {errors.confirmPassword && <span className="text-xs text-red-500">{errors.confirmPassword.message}</span>}
                    </Field>

                    {error && <div className="p-3 bg-red-50 text-red-600 text-sm rounded-lg border border-red-100">{error}</div>}

                    <Button type="submit" className="w-full mt-2" disabled={isSubmitting}>
                        {isSubmitting ? 'Регистрация...' : 'Зарегистрироваться'}
                    </Button>
                </form>

                <p className="text-center text-sm text-muted mt-6">
                    Уже есть аккаунт? <Link to="/login" className="text-accent hover:underline">Войти</Link>
                </p>
            </div>
        </div>
    );
}