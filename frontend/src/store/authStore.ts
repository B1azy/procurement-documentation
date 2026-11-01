import { create } from 'zustand';

export interface UserProfile {
    full_name: string;
    email: string;
}

interface AuthState {
    token: string | null;
    user: UserProfile | null;
    login: (token: string, user: UserProfile) => void;
    logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
    token: localStorage.getItem('access_token'),
    user: JSON.parse(localStorage.getItem('user_profile') || 'null'),

    login: (token, user) => {
        localStorage.setItem('access_token', token);
        localStorage.setItem('user_profile', JSON.stringify(user));
        set({ token, user });
    },

    logout: () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('user_profile');
        set({ token: null, user: null });
    },
}));