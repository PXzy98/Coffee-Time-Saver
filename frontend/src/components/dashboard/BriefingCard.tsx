import Markdown from 'react-markdown';
import type { BriefingOut, Locale } from '../../types';
import { Panel } from '../common/Panel';
import { LoadingState } from '../common/PageState';
import { formatDateTime } from '../../utils/format';

interface BriefingCardProps {
  title: string;
  briefing: BriefingOut | null;
  locale: Locale;
  loading?: boolean;
}

export function BriefingCard({ title, briefing, locale, loading }: BriefingCardProps) {
  const content = locale === 'fr' ? briefing?.content_fr ?? briefing?.content_en : briefing?.content_en ?? briefing?.content_fr;

  return (
    <Panel title={title} subtitle={briefing ? formatDateTime(briefing.generated_at, locale) : undefined}>
      {loading ? (
        <LoadingState title="Loading briefing…" />
      ) : (
        <div className="briefing-card">
          <article className="briefing-content">
            {content ? <Markdown>{content}</Markdown> : 'No briefing content available.'}
          </article>
        </div>
      )}
    </Panel>
  );
}
