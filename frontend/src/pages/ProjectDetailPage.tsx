import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useParams } from 'react-router-dom';
import { getApiErrorMessage } from '../api/client';
import { getProject, toggleProjectShare, updateProject } from '../api/projects';
import { ErrorState, LoadingState } from '../components/common/PageState';
import { Panel } from '../components/common/Panel';
import { isAdmin, useAuthStore } from '../store/authStore';
import { useUiStore } from '../store/uiStore';
import type { ProjectOut } from '../types';
import { formatDate } from '../utils/format';

export function ProjectDetailPage() {
  const { t } = useTranslation();
  const locale = useUiStore((state) => state.language);
  const pushToast = useUiStore((state) => state.pushToast);
  const user = useAuthStore((state) => state.user);
  const { projectId } = useParams();

  const [project, setProject] = useState<ProjectOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [form, setForm] = useState({
    name: '',
    description: '',
    status: 'active',
  });

  const admin = isAdmin(user);

  const loadProject = useCallback(async () => {
    if (!projectId) {
      setErrorMessage('Project id missing');
      setLoading(false);
      return;
    }

    setErrorMessage(null);
    try {
      const data = await getProject(projectId);
      setProject(data);
      setForm({
        name: data.name,
        description: data.description ?? '',
        status: data.status,
      });
    } catch (error) {
      setErrorMessage(getApiErrorMessage(error));
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    void loadProject();
  }, [loadProject]);

  const prettyMetadata = useMemo(() => JSON.stringify(project?.metadata ?? {}, null, 2), [project?.metadata]);

  async function handleSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!projectId) {
      return;
    }

    setSaving(true);
    try {
      const updated = await updateProject(projectId, {
        name: form.name,
        description: form.description || null,
        status: form.status,
      });
      setProject(updated);
      pushToast({
        tone: 'success',
        title: t('common.save'),
      });
    } catch (error) {
      pushToast({
        tone: 'error',
        title: t('states.errorTitle'),
        message: getApiErrorMessage(error),
      });
    } finally {
      setSaving(false);
    }
  }

  async function handleToggleShare() {
    if (!projectId || !project) {
      return;
    }

    setSaving(true);
    try {
      const updated = await toggleProjectShare(projectId, !project.is_shared);
      setProject(updated);
    } catch (error) {
      pushToast({
        tone: 'error',
        title: t('states.errorTitle'),
        message: getApiErrorMessage(error),
      });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="page-stack">
      <header className="page-header">
        <div>
          <Link to="/projects" className="ghost-link">
            ← {t('nav.projects')}
          </Link>
          <h1>{project?.name ?? t('projects.details')}</h1>
          <p>{project?.description ?? t('projects.subtitle')}</p>
        </div>
      </header>

      {loading ? <LoadingState title={t('common.loading')} /> : null}

      {!loading && errorMessage ? (
        <ErrorState
          title={t('states.errorTitle')}
          message={errorMessage}
          action={
            <button type="button" className="secondary-button" onClick={() => void loadProject()}>
              {t('common.retry')}
            </button>
          }
        />
      ) : null}

      {project ? (
        <>
          <div className="two-column-grid">
            <Panel
              title={t('projects.details')}
              actions={
                admin ? (
                  <button type="button" className="secondary-button" onClick={() => void handleToggleShare()} disabled={saving}>
                    {project.is_shared ? 'Unshare' : 'Share'}
                  </button>
                ) : null
              }
            >
              {admin ? (
                <form className="form-grid padded-form" onSubmit={handleSave}>
                  <label className="field">
                    <span>Name</span>
                    <input value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} />
                  </label>

                  <label className="field">
                    <span>{t('tasks.taskDescription')}</span>
                    <textarea
                      value={form.description}
                      onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))}
                      rows={4}
                    />
                  </label>

                  <label className="field">
                    <span>{t('common.status')}</span>
                    <select
                      value={form.status}
                      onChange={(event) => setForm((current) => ({ ...current, status: event.target.value }))}
                    >
                      <option value="active">active</option>
                      <option value="paused">paused</option>
                      <option value="archived">archived</option>
                    </select>
                  </label>

                  <div className="form-actions">
                    <button type="submit" className="primary-button" disabled={saving}>
                      {saving ? t('common.loading') : t('common.save')}
                    </button>
                  </div>
                </form>
              ) : (
                <div className="detail-list padded-panel">
                  <div>
                    <span>{t('common.status')}</span>
                    <strong>{project.status}</strong>
                  </div>
                  <div>
                    <span>{t('projects.shared')}</span>
                    <strong>{project.is_shared ? t('common.yes') : t('common.no')}</strong>
                  </div>
                  <div>
                    <span>{t('projects.owner')}</span>
                    <strong>{project.owner_id ?? '—'}</strong>
                  </div>
                  <div>
                    <span>Created</span>
                    <strong>{formatDate(project.created_at, locale)}</strong>
                  </div>
                </div>
              )}
            </Panel>

            <Panel title={t('projects.members')}>
              <div className="panel-body padded-panel">
                <div className="tag-cloud">
                  {project.members.map((member) => (
                    <span key={member.user_id} className="tag">
                      {member.role}: {member.user_id}
                    </span>
                  ))}
                </div>
              </div>
            </Panel>
          </div>

          <div className="two-column-grid">
            <Panel title={t('projects.metadata')}>
              <pre className="code-block">{prettyMetadata}</pre>
            </Panel>
            <Panel title="Backend-aligned placeholders">
              <div className="placeholder-list padded-panel">
                <p>{t('projects.placeholderDocuments')}</p>
                <p>{t('projects.placeholderTasks')}</p>
                <p>{t('projects.placeholderTimeline')}</p>
                <p>{t('projects.placeholderRisk')}</p>
              </div>
            </Panel>
          </div>
        </>
      ) : null}
    </div>
  );
}
