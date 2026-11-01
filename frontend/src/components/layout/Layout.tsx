import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';

export function Layout() {
    return (
        <div className="min-h-screen bg-page">
            <Sidebar />
            <main className="pl-[260px]">
                <div className="mx-auto max-w-[1100px] px-10 py-10">
                    <Outlet />
                </div>
            </main>
        </div>
    );
}