import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Layout } from './components/layout/Layout';
import { Home } from './pages/Home';
import { NewRequest } from './pages/NewRequest';
import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { useAuthStore } from './store/authStore';
import { Clarify } from './pages/Clarify';
import { TZView } from './pages/TZView';
import { Projects } from './pages/Projects';
import toast, { Toaster } from 'react-hot-toast';

const queryClient = new QueryClient();

// Обертка для защиты: если нет токена — редирект на логин
function ProtectedRoute() {
  const token = useAuthStore((state) => state.token);
  if (!token) return <Navigate to="/login" replace />;
  return <Outlet />;
}

function Placeholder({ title }: { title: string }) {
  return (
    <div className="bg-white rounded-card border border-border p-10 flex flex-col items-center justify-center h-[400px]">
      <div className="text-4xl mb-4">🚧</div>
      <h2 className="text-xl font-bold mb-2">{title}</h2>
      <p className="text-muted">Раздел в разработке</p>
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Toaster position="top-right" />
      <BrowserRouter>
        <Routes>
          {/* Публичные роуты */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          {/* Защищенные роуты */}
          <Route element={<ProtectedRoute />}>
            <Route path="/" element={<Layout />}>
              <Route index element={<Home />} />
              <Route path="requests/new" element={<NewRequest />} />
              <Route path="requests/:id/clarify" element={<Clarify />} />
              <Route path="requests/:id/tz" element={<TZView />} />
              <Route path="projects" element={<Projects />} />
              <Route path="templates" element={<Placeholder title="Шаблоны" />} />
              <Route path="contractors" element={<Placeholder title="База подрядчиков" />} />
              <Route path="settings" element={<Placeholder title="Настройки" />} />
            </Route>
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}