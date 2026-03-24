import { Outlet } from 'react-router-dom';
import { useWebSocket } from '../../hooks/useWebSocket';
import { ToastHost } from '../common/ToastHost';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';

export function MainLayout() {
  useWebSocket();

  return (
    <div className="app-shell">
      <Sidebar />
      <div className="app-content">
        <TopBar />
        <main className="page-shell">
          <Outlet />
        </main>
      </div>
      <ToastHost />
    </div>
  );
}
