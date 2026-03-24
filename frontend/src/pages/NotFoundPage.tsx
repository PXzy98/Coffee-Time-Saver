import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Panel } from '../components/common/Panel';

export function NotFoundPage() {
  const { t } = useTranslation();

  return (
    <div className="page-stack narrow-page">
      <Panel title={t('states.notFound')}>
        <div className="state-card">
          <Link className="primary-button" to="/dashboard">
            {t('nav.dashboard')}
          </Link>
        </div>
      </Panel>
    </div>
  );
}
