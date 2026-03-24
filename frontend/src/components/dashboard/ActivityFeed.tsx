import type { ActivityItem, Locale } from '../../types';
import { formatDateTime, toTitleCase } from '../../utils/format';

interface ActivityFeedProps {
  items: ActivityItem[];
  locale: Locale;
}

export function ActivityFeed({ items, locale }: ActivityFeedProps) {
  return (
    <div className="activity-feed">
      {items.map((item) => (
        <article key={`${item.action}-${item.created_at}-${item.entity_id ?? ''}`} className="activity-item">
          <div>
            <p className="activity-title">{toTitleCase(item.action)}</p>
            <p className="activity-meta">
              {[item.entity_type, item.entity_id].filter(Boolean).join(' · ') || 'system'}
            </p>
          </div>
          <p className="activity-time">{formatDateTime(item.created_at, locale)}</p>
        </article>
      ))}
    </div>
  );
}
