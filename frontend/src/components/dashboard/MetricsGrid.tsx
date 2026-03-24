import { useTranslation } from 'react-i18next';
import type { Locale, MetricsOut } from '../../types';
import { formatNumber } from '../../utils/format';

interface MetricsGridProps {
  metrics: MetricsOut;
  locale: Locale;
}

export function MetricsGrid({ metrics, locale }: MetricsGridProps) {
  const { t } = useTranslation();

  const items = [
    { label: t('dashboard.activeProjects'), value: metrics.active_projects, tone: 'earth' },
    { label: t('dashboard.overdueTasks'), value: metrics.overdue_tasks, tone: 'danger' },
    { label: t('dashboard.openTasks'), value: metrics.pending_tasks, tone: 'accent' },
    { label: t('dashboard.filesProcessedToday'), value: metrics.files_processed_today, tone: 'neutral' },
    { label: t('dashboard.unreadEmails'), value: metrics.unread_emails, tone: 'warm' },
  ] as const;

  return (
    <div className="metrics-grid">
      {items.map((item) => (
        <article key={item.label} className={`metric-card metric-card-${item.tone}`}>
          <p className="metric-label">{item.label}</p>
          <p className="metric-value">{formatNumber(item.value, locale)}</p>
        </article>
      ))}
    </div>
  );
}
