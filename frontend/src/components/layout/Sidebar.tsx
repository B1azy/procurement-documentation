import { NavLink } from 'react-router-dom';
import { LayoutDashboard, PlusCircle, FolderOpen, FileText, Users, Settings } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import { LogOut } from 'lucide-react';

const navItems = [
    { to: '/', label: 'Главная', icon: LayoutDashboard },
    { to: '/requests/new', label: 'Новый запрос', icon: PlusCircle },
    { to: '/projects', label: 'Мои проекты', icon: FolderOpen },
    { to: '/templates', label: 'Шаблоны', icon: FileText },
    { to: '/contractors', label: 'База подрядчиков', icon: Users },
    { to: '/settings', label: 'Настройки', icon: Settings },
];

export function Sidebar() {
    const navigate = useNavigate();
    const logout = useAuthStore((state) => state.logout);
    const user = useAuthStore((state) => state.user);

    const initials = user?.full_name
        ? user.full_name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase()
        : 'П';

    const handleLogout = () => {
        logout();
        navigate('/login');
    };
    return (
        <aside className="fixed left-0 top-0 z-10 h-screen w-[260px] bg-navy flex flex-col justify-between p-6 text-white">
            <div>
                {/* Логотип */}
                <div className="flex items-center gap-3 mb-10">
                    <div className="h-10 w-10 rounded-xl bg-accent flex items-center justify-center font-bold text-xl">
                        AI
                    </div>
                    <div>
                        <div className="font-bold text-[15px] leading-tight">Закупки AI</div>
                        <div className="text-xs text-blue-200/80">ИИ-агент документации</div>
                    </div>
                </div>

                {/* Навигация */}
                <nav className="space-y-2">
                    {navItems.map((item) => (
                        <NavLink
                            key={item.to}
                            to={item.to}
                            className={({ isActive }) =>
                                `flex items-center gap-3 px-4 py-3 rounded-btn transition-colors text-[14px] ${isActive
                                    ? 'bg-accent text-white font-medium'
                                    : 'text-blue-100/70 hover:bg-white/5 hover:text-white'
                                }`
                            }
                        >
                            <item.icon size={18} />
                            {item.label}
                        </NavLink>
                    ))}
                </nav>
            </div>

            {/* Пользователь */}
            <div className="pt-6 border-t border-white/10">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="h-9 w-9 rounded-full bg-accent-soft text-accent flex items-center justify-center font-bold text-sm">
                            {initials}
                        </div>
                        <div className="max-w-[140px]">
                            <div className="text-sm font-medium truncate" title={user?.full_name}>
                                {user?.full_name || 'Пользователь'}
                            </div>
                            <div className="text-xs text-blue-200/60 truncate">
                                {user?.email || 'Менеджер'}
                            </div>
                        </div>
                    </div>
                    <button onClick={() => { logout(); navigate('/login'); }} className="p-2 text-blue-200/60 hover:text-white transition-colors" title="Выйти">
                        <LogOut size={18} />
                    </button>
                </div>
            </div>
        </aside>
    );
}