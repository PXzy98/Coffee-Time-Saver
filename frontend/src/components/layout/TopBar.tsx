import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { logout } from '../../api/auth';
import { getEmailStatus } from '../../api/settings';
import { useAuthStore } from '../../store/authStore';
import { useUiStore } from '../../store/uiStore';

export function TopBar() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const clearSession = useAuthStore((state) => state.clearSession);
  const language = useUiStore((state) => state.language);
  const setLanguage = useUiStore((state) => state.setLanguage);
  const sidebarOpen = useUiStore((state) => state.sidebarOpen);
  const setSidebarOpen = useUiStore((state) => state.setSidebarOpen);
  const websocketStatus = useUiStore((state) => state.websocketStatus);
  const notifications = useUiStore((state) => state.notifications);
  const markNotificationsSeen = useUiStore((state) => state.markNotificationsSeen);

  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [emailStatus, setEmailStatus] = useState<{ configured: boolean; connected: boolean } | null>(null);

  useEffect(() => {
    getEmailStatus()
      .then(setEmailStatus)
      .catch(() => setEmailStatus({ configured: false, connected: false }));
  }, []);

  const emailBotLabel = useMemo(() => {
    if (!emailStatus) return null;
    if (!emailStatus.configured) return t('topbar.emailBotNotConfigured');
    if (emailStatus.connected) return t('topbar.emailBotConnected');
    return t('topbar.emailBotDisconnected');
  }, [t, emailStatus]);

  const emailBotPillClass = useMemo(() => {
    if (!emailStatus || !emailStatus.configured) return 'status-pill status-pill-disconnected';
    if (emailStatus.connected) return 'status-pill status-pill-connected';
    return 'status-pill status-pill-disconnected';
  }, [emailStatus]);

  const unreadCount = useMemo(
    () => notifications.filter((notification) => notification.unread).length,
    [notifications],
  );

  const websocketLabel = useMemo(() => {
    if (websocketStatus === 'connected') {
      return t('topbar.websocketConnected');
    }
    if (websocketStatus === 'connecting') {
      return t('topbar.websocketConnecting');
    }
    return t('topbar.websocketDisconnected');
  }, [t, websocketStatus]);

  async function handleLogout() {
    try {
      await logout();
    } catch {
      // Best effort logout, local session still gets cleared.
    } finally {
      clearSession();
      navigate('/login');
    }
  }

  function handleNotificationsToggle() {
    const next = !notificationsOpen;
    setNotificationsOpen(next);
    if (next) {
      markNotificationsSeen();
    }
  }

  return (
    <header className="topbar">
      <div className="topbar-left">
        <button
          type="button"
          className="icon-button mobile-only"
          onClick={() => setSidebarOpen(!sidebarOpen)}
          aria-label="Toggle navigation"
        >
          ☰
        </button>
        <div className={`status-pill status-pill-${websocketStatus}`}>{websocketLabel}</div>
        {emailBotLabel !== null && (
          <div className={emailBotPillClass}>{emailBotLabel}</div>
        )}
      </div>

      <div className="topbar-right">
        <div className="segmented-control">
          <button
            type="button"
            className={language === 'en' ? 'segmented-control-active' : ''}
            onClick={() => setLanguage('en')}
          >
            EN
          </button>
          <button
            type="button"
            className={language === 'fr' ? 'segmented-control-active' : ''}
            onClick={() => setLanguage('fr')}
          >
            FR
          </button>
        </div>

        <div className="notification-shell">
          <button type="button" className="icon-button" onClick={handleNotificationsToggle}>
            {t('topbar.notifications')}
            {unreadCount ? <span className="notification-count">{unreadCount}</span> : null}
          </button>
          {notificationsOpen ? (
            <div className="notification-panel">
              {notifications.length ? (
                notifications.map((item) => (
                  <article key={item.id} className={`notification-item${item.unread ? ' notification-item-unread' : ''}`}>
                    <p className="notification-title">{item.title}</p>
                    {item.message ? <p className="notification-message">{item.message}</p> : null}
                    <p className="notification-time">{new Date(item.createdAt).toLocaleString()}</p>
                  </article>
                ))
              ) : (
                <p className="notification-empty">{t('common.empty')}</p>
              )}
            </div>
          ) : null}
        </div>

        <div className="user-chip">
          <div>
            <p className="user-chip-name">{user?.display_name}</p>
            <p className="user-chip-meta">{user?.roles.join(', ')}</p>
          </div>
          <button type="button" className="ghost-button" onClick={handleLogout}>
            {t('topbar.logout')}
          </button>
        </div>
      </div>
    </header>
  );
}
