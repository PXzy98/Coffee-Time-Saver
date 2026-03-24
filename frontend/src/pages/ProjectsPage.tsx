import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { getApiErrorMessage } from '../api/client';
import { createProject, listProjects } from '../api/projects';
import { EmptyState, ErrorState, LoadingState } from '../components/common/PageState';
import { Panel } from '../components/common/Panel';
import { isAdmin, useAuthStore } from '../store/authStore';
import { useUiStore } from '../store/uiStore';
import type { ProjectCreate, ProjectOut } from '../types';
import { formatDate } from '../utils/format';

const initialProjectForm: ProjectCreate = {
  name: '',
  description: '',
  status: 'active',
  metadata: {},
};

export function ProjectsPage() {
  const { t } = useTranslation();
  const locale = useUiStore((state) => state.language);
  const pushToast = useUiStore((state) => state.pushToast);
  const user = useAuthStore((state) => state.user);

  const [projects, setProjects] = useState<ProjectOut[]>([]);
  const [form, setForm] = useState<ProjectCreate>(initialProjectForm);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const admin = isAdmin(user);

  const loadProjects = useCallback(async () => {
    setErrorMessage(null);
    try {
      const data = await listProjects();
      setProjects(data);
    } catch (error) {
      setErrorMessage(getApiErrorMessage(error));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadProjects();
  }, [loadProjects]);

  const [myProjects, sharedProjects] = useMemo(() => {
    const mine: ProjectOut[] = [];
    const shared: ProjectOut[] = [];
    for (const project of projects) {
      const belongsToUser =
        project.owner_id === user?.id || project.members.some((member) => member.user_id === user?.id);
      if (belongsToUser) {
        mine.push(project);
      } else if (project.is_shared) {
        shared.push(project);
      }
    }
    return [mine, shared];
  }, [projects, user?.id]);

  async function handleCreateProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);

    try {
      const created = await createProject({
        name: form.name,
        description: form.description?.trim() || undefined,
        status: form.status || 'active',
        metadata: form.metadata ?? {},
      });
      setProjects((current) => [created, ...current]);
      setForm(initialProjectForm);
      pushToast({
        tone: 'success',
        title: t('projects.createProject'),
      });
    } catch (error) {
      pushToast({
        tone: 'error',
        title: t('states.errorTitle'),
        message: getApiErrorMessage(error),
      });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="page-stack">
      <header className="page-header">
        <div>
          <h1>{t('projects.title')}</h1>
          <p>{t('projects.subtitle')}</p>
        </div>
      </header>

      {admin ? (
        <Panel title={t('projects.createProject')}>
          <form className="form-grid padded-form" onSubmit={handleCreateProject}>
            <div className="two-column-grid">
              <label className="field">
                <span>Name</span>
                <input
                  value={form.name}
                  onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
                  required
                />
              </label>
              <label className="field">
                <span>{t('common.status')}</span>
                <select
                  value={form.status ?? 'active'}
                  onChange={(event) => setForm((current) => ({ ...current, status: event.target.value }))}
                >
                  <option value="active">active</option>
                  <option value="paused">paused</option>
                  <option value="archived">archived</option>
                </select>
              </label>
            </div>

            <label className="field">
              <span>{t('tasks.taskDescription')}</span>
              <textarea
                value={form.description ?? ''}
                onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))}
                rows={3}
              />
            </label>

            <div className="form-actions">
              <button type="submit" className="primary-button" disabled={submitting}>
                {submitting ? t('common.loading') : t('common.create')}
              </button>
            </div>
          </form>
        </Panel>
      ) : null}

      {loading ? <LoadingState title={t('common.loading')} /> : null}

      {!loading && errorMessage ? (
        <ErrorState
          title={t('states.errorTitle')}
          message={errorMessage}
          action={
            <button type="button" className="secondary-button" onClick={() => void loadProjects()}>
              {t('common.retry')}
            </button>
          }
        />
      ) : null}

      {!loading && !errorMessage ? (
        <div className="two-column-grid">
          <Panel title={t('projects.myProjects')}>
            <div className="panel-body padded-panel">
              {myProjects.length ? (
                <div className="card-list">
                  {myProjects.map((project) => (
                    <Link key={project.id} to={`/projects/${project.id}`} className="project-card">
                      <div className="project-card-header">
                        <div>
                          <h3>{project.name}</h3>
                          <p>{project.description || 'No description'}</p>
                        </div>
                        <span className={`badge badge-${project.status === 'active' ? 'medium' : 'low'}`}>{project.status}</span>
                      </div>
                      <div className="project-meta-grid">
                        <span>{formatDate(project.created_at, locale)}</span>
                        <span>{project.members.length} members</span>
                        <span>{project.is_shared ? t('projects.shared') : t('common.readOnly')}</span>
                      </div>
                    </Link>
                  ))}
                </div>
              ) : (
                <EmptyState title={t('states.emptyTitle')} message="No owned or member projects." />
              )}
            </div>
          </Panel>

          <Panel title={t('projects.sharedProjects')}>
            <div className="panel-body padded-panel">
              {sharedProjects.length ? (
                <div className="card-list">
                  {sharedProjects.map((project) => (
                    <Link key={project.id} to={`/projects/${project.id}`} className="project-card">
                      <div className="project-card-header">
                        <div>
                          <h3>{project.name}</h3>
                          <p>{project.description || 'No description'}</p>
                        </div>
                        <span className="badge badge-medium">{t('projects.shared')}</span>
                      </div>
                      <div className="project-meta-grid">
                        <span>{formatDate(project.created_at, locale)}</span>
                        <span>{project.members.length} members</span>
                        <span>{project.status}</span>
                      </div>
                    </Link>
                  ))}
                </div>
              ) : (
                <EmptyState title={t('states.emptyTitle')} message="No shared projects available." />
              )}
            </div>
          </Panel>
        </div>
      ) : null}
    </div>
  );
}
