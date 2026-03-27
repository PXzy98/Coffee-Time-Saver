import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { getDashboard, getTodayBriefing } from '../api/dashboard';
import { getApiErrorMessage } from '../api/client';
import { ActivityFeed } from '../components/dashboard/ActivityFeed';
import { BriefingCard } from '../components/dashboard/BriefingCard';
import { MetricsGrid } from '../components/dashboard/MetricsGrid';
import { ErrorState, LoadingState } from '../components/common/PageState';
import { Panel } from '../components/common/Panel';
import { useWsEvent } from '../hooks/useWsEvent';
import { useUiStore } from '../store/uiStore';
import type { BriefingOut, DashboardOut } from '../types';

export function DashboardPage() {
  const { t } = useTranslation();
  const locale = useUiStore((state) => state.language);

  const [dashboard, setDashboard] = useState<DashboardOut | null>(null);
  const [briefing, setBriefing] = useState<BriefingOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setErrorMessage(null);
    const [dashboardResult, briefingResult] = await Promise.allSettled([getDashboard(), getTodayBriefing()]);

    if (dashboardResult.status === 'fulfilled') {
      setDashboard(dashboardResult.value);
    } else {
      setErrorMessage(getApiErrorMessage(dashboardResult.reason));
    }

    if (briefingResult.status === 'fulfilled') {
      setBriefing(briefingResult.value);
    }

    setLoading(false);
  }, []);

  useWsEvent(
    useCallback(
      (event) => {
        if (['dashboard.refresh', 'task.updated', 'file.status_changed'].includes(event.type)) {
          void loadData();
        }
      },
      [loadData],
    ),
  );

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const quickActions = useMemo(
    () => [
      { to: '/tasks', label: t('dashboard.goTasks'), style: 'primary-button' },
      { to: '/upload', label: t('dashboard.goUpload'), style: 'secondary-button' },
      { to: '/projects', label: t('dashboard.goProjects'), style: 'ghost-button' },
    ],
    [t],
  );

  return (
    <div className="page-stack">
      <header className="page-header">
        <div>
          <h1>{t('dashboard.title')}</h1>
          <p>{t('dashboard.subtitle')}</p>
        </div>
        <button type="button" className="secondary-button" onClick={() => void loadData()}>
          {t('common.refresh')}
        </button>
      </header>

      {loading && !dashboard ? <LoadingState title={t('common.loading')} /> : null}

      {!loading && errorMessage ? (
        <ErrorState
          title={t('states.errorTitle')}
          message={errorMessage}
          action={
            <button type="button" className="secondary-button" onClick={() => void loadData()}>
              {t('common.retry')}
            </button>
          }
        />
      ) : null}

      {!loading || briefing ? (
        <BriefingCard title={t('dashboard.briefing')} briefing={briefing} locale={locale} loading={loading && !briefing} />
      ) : null}

      {dashboard ? (
        <>
          <Panel title={t('dashboard.metrics')}>
            <div className="panel-body padded-panel">
              <MetricsGrid metrics={dashboard.metrics} locale={locale} />
            </div>
          </Panel>

          <div className="two-column-grid">
            <Panel title={t('dashboard.activity')}>
              <div className="panel-body padded-panel">
                <ActivityFeed items={dashboard.recent_activity} locale={locale} />
              </div>
            </Panel>

            <Panel title={t('dashboard.quickActions')}>
              <div className="panel-body padded-panel quick-actions">
                {quickActions.map((action) => (
                  <Link key={action.to} to={action.to} className={action.style}>
                    {action.label}
                  </Link>
                ))}
              </div>
            </Panel>
          </div>
        </>
      ) : null}
    </div>
  );
}
