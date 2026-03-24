import { NavLink } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useUiStore } from '../../store/uiStore';

const NAV_ITEMS = [
  { to: '/dashboard', key: 'dashboard' },
  { to: '/tasks', key: 'tasks' },
  { to: '/projects', key: 'projects' },
  { to: '/tools', key: 'tools' },
  { to: '/upload', key: 'upload' },
  { to: '/settings', key: 'settings' },
] as const;

export function Sidebar() {
  const { t } = useTranslation();
  const sidebarOpen = useUiStore((state) => state.sidebarOpen);
  const setSidebarOpen = useUiStore((state) => state.setSidebarOpen);

  return (
    <>
      <div
        className={`sidebar-backdrop${sidebarOpen ? ' sidebar-backdrop-visible' : ''}`}
        onClick={() => setSidebarOpen(false)}
      />
      <aside className={`sidebar${sidebarOpen ? ' sidebar-open' : ''}`}>
        <div className="sidebar-brand">
          <span className="sidebar-badge">CTS</span>
          <div>
            <p className="sidebar-eyebrow">Workspace</p>
            <h1>{t('appName')}</h1>
          </div>
        </div>

        <nav className="sidebar-nav">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => `sidebar-link${isActive ? ' sidebar-link-active' : ''}`}
              onClick={() => setSidebarOpen(false)}
            >
              {t(`nav.${item.key}`)}
            </NavLink>
          ))}
        </nav>
      </aside>
    </>
  );
}
