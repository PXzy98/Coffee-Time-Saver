import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { getApiErrorMessage } from '../api/client';
import { listProjects } from '../api/projects';
import { createTask, deleteTask, listTasks, updateTask } from '../api/tasks';
import { EmptyState, ErrorState, LoadingState } from '../components/common/PageState';
import { Panel } from '../components/common/Panel';
import { useWsEvent } from '../hooks/useWsEvent';
import { useUiStore } from '../store/uiStore';
import type { ProjectOut, TaskCreate, TaskOut } from '../types';
import { formatDate } from '../utils/format';

type PriorityFilter = 'all' | 'low' | 'medium' | 'high';

function classifyPriority(priority: number): PriorityFilter {
  if (priority >= 75) {
    return 'high';
  }
  if (priority >= 40) {
    return 'medium';
  }
  return 'low';
}

const initialForm: TaskCreate = {
  title: '',
  description: '',
  priority: 50,
  due_date: null,
  scheduled_at: null,
  project_id: null,
  source: 'manual',
};

export function TasksPage() {
  const { t } = useTranslation();
  const locale = useUiStore((state) => state.language);
  const pushToast = useUiStore((state) => state.pushToast);

  const [tasks, setTasks] = useState<TaskOut[]>([]);
  const [projects, setProjects] = useState<ProjectOut[]>([]);
  const [form, setForm] = useState<TaskCreate>(initialForm);
  const [filters, setFilters] = useState({
    projectId: 'all',
    source: 'all',
    priority: 'all' as PriorityFilter,
  });
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [busyTaskId, setBusyTaskId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setErrorMessage(null);
    try {
      const [taskData, projectData] = await Promise.all([listTasks(), listProjects()]);
      setTasks(taskData);
      setProjects(projectData);
    } catch (error) {
      setErrorMessage(getApiErrorMessage(error));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  useWsEvent(
    useCallback(
      (event) => {
        if (event.type === 'task.updated') {
          void loadData();
        }
      },
      [loadData],
    ),
  );

  const projectMap = useMemo(
    () => new Map(projects.map((project) => [project.id, project.name])),
    [projects],
  );

  const sources = useMemo(() => Array.from(new Set(tasks.map((task) => task.source))).sort(), [tasks]);

  const filteredTasks = useMemo(() => {
    return tasks.filter((task) => {
      const projectMatch = filters.projectId === 'all' || task.project_id === filters.projectId;
      const sourceMatch = filters.source === 'all' || task.source === filters.source;
      const priorityMatch = filters.priority === 'all' || classifyPriority(task.priority) === filters.priority;
      return projectMatch && sourceMatch && priorityMatch;
    });
  }, [filters.priority, filters.projectId, filters.source, tasks]);

  async function handleCreateTask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);

    try {
      const response = await createTask({
        title: form.title,
        description: form.description?.trim() || undefined,
        priority: form.priority,
        due_date: form.due_date || null,
        scheduled_at: form.scheduled_at || null,
        project_id: form.project_id || null,
        source: form.source || 'manual',
      });
      setTasks(response);
      setForm(initialForm);
      pushToast({
        tone: 'success',
        title: t('tasks.newTask'),
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

  async function handleCompleteTask(taskId: string) {
    setBusyTaskId(taskId);
    try {
      const response = await updateTask(taskId, { is_completed: true });
      setTasks(response);
    } catch (error) {
      pushToast({
        tone: 'error',
        title: t('states.errorTitle'),
        message: getApiErrorMessage(error),
      });
    } finally {
      setBusyTaskId(null);
    }
  }

  async function handleDeleteTask(taskId: string) {
    setBusyTaskId(taskId);
    try {
      await deleteTask(taskId);
      await loadData();
    } catch (error) {
      pushToast({
        tone: 'error',
        title: t('states.errorTitle'),
        message: getApiErrorMessage(error),
      });
    } finally {
      setBusyTaskId(null);
    }
  }

  return (
    <div className="page-stack">
      <header className="page-header">
        <div>
          <h1>{t('tasks.title')}</h1>
          <p>{t('tasks.subtitle')}</p>
        </div>
      </header>

      <div className="two-column-grid">
        <Panel title={t('tasks.newTask')}>
          <form className="form-grid padded-form" onSubmit={handleCreateTask}>
            <label className="field">
              <span>{t('tasks.taskTitle')}</span>
              <input
                value={form.title}
                onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))}
                required
              />
            </label>

            <label className="field">
              <span>{t('tasks.taskDescription')}</span>
              <textarea
                value={form.description ?? ''}
                onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))}
                rows={4}
              />
            </label>

            <div className="three-column-grid">
              <label className="field">
                <span>{t('tasks.priority')}</span>
                <input
                  value={form.priority ?? 50}
                  onChange={(event) => setForm((current) => ({ ...current, priority: Number(event.target.value) }))}
                  type="number"
                  min={0}
                  max={100}
                />
              </label>

              <label className="field">
                <span>{t('tasks.dueDate')}</span>
                <input
                  value={form.due_date ?? ''}
                  onChange={(event) => setForm((current) => ({ ...current, due_date: event.target.value || null }))}
                  type="date"
                />
              </label>

              <label className="field">
                <span>{t('tasks.project')}</span>
                <select
                  value={form.project_id ?? ''}
                  onChange={(event) => setForm((current) => ({ ...current, project_id: event.target.value || null }))}
                >
                  <option value="">{t('tasks.allProjects')}</option>
                  {projects.map((project) => (
                    <option key={project.id} value={project.id}>
                      {project.name}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <label className="field">
              <span>{t('tasks.scheduledAt')}</span>
              <input
                value={form.scheduled_at ?? ''}
                onChange={(event) => setForm((current) => ({ ...current, scheduled_at: event.target.value || null }))}
                type="datetime-local"
              />
            </label>

            <label className="field">
              <span>{t('tasks.source')}</span>
              <input
                value={form.source ?? 'manual'}
                onChange={(event) => setForm((current) => ({ ...current, source: event.target.value }))}
              />
            </label>

            <div className="form-actions">
              <button type="submit" className="primary-button" disabled={submitting}>
                {submitting ? t('common.loading') : t('common.create')}
              </button>
            </div>
          </form>
        </Panel>

        <Panel title={t('tasks.filters')}>
          <div className="form-grid padded-form">
            <label className="field">
              <span>{t('tasks.project')}</span>
              <select
                value={filters.projectId}
                onChange={(event) => setFilters((current) => ({ ...current, projectId: event.target.value }))}
              >
                <option value="all">{t('tasks.allProjects')}</option>
                {projects.map((project) => (
                  <option key={project.id} value={project.id}>
                    {project.name}
                  </option>
                ))}
              </select>
            </label>

            <label className="field">
              <span>{t('tasks.source')}</span>
              <select
                value={filters.source}
                onChange={(event) => setFilters((current) => ({ ...current, source: event.target.value }))}
              >
                <option value="all">{t('tasks.allSources')}</option>
                {sources.map((source) => (
                  <option key={source} value={source}>
                    {source}
                  </option>
                ))}
              </select>
            </label>

            <label className="field">
              <span>{t('tasks.priority')}</span>
              <select
                value={filters.priority}
                onChange={(event) =>
                  setFilters((current) => ({ ...current, priority: event.target.value as PriorityFilter }))
                }
              >
                <option value="all">{t('tasks.allPriorities')}</option>
                <option value="low">{t('tasks.priorityLow')}</option>
                <option value="medium">{t('tasks.priorityMedium')}</option>
                <option value="high">{t('tasks.priorityHigh')}</option>
              </select>
            </label>
          </div>
        </Panel>
      </div>

      <Panel title={t('nav.tasks')} subtitle={`${filteredTasks.length} items`}>
        {loading ? (
          <LoadingState title={t('common.loading')} />
        ) : errorMessage ? (
          <ErrorState
            title={t('states.errorTitle')}
            message={errorMessage}
            action={
              <button type="button" className="secondary-button" onClick={() => void loadData()}>
                {t('common.retry')}
              </button>
            }
          />
        ) : filteredTasks.length ? (
          <div className="task-list">
            {filteredTasks.map((task) => {
              const priorityClass = `badge-${classifyPriority(task.priority)}`;
              const projectName = task.project_id ? projectMap.get(task.project_id) : null;
              return (
                <article key={task.id} className="task-card">
                  <div className="task-card-main">
                    <div className="task-title-row">
                      <h3>{task.title}</h3>
                      <span className={`badge ${priorityClass}`}>{task.priority}</span>
                    </div>
                    {task.description ? <p className="task-description">{task.description}</p> : null}
                    <div className="task-meta">
                      <span>{task.source}</span>
                      <span>{projectName ?? 'No project'}</span>
                      <span>{formatDate(task.due_date, locale)}</span>
                      {task.scheduled_at ? <span>{t('tasks.scheduledAt')}: {formatDate(task.scheduled_at, locale)}</span> : null}
                    </div>
                  </div>

                  <div className="task-card-actions">
                    <button
                      type="button"
                      className="secondary-button"
                      onClick={() => void handleCompleteTask(task.id)}
                      disabled={busyTaskId === task.id}
                    >
                      {t('tasks.complete')}
                    </button>
                    <button
                      type="button"
                      className="danger-button"
                      onClick={() => void handleDeleteTask(task.id)}
                      disabled={busyTaskId === task.id}
                    >
                      {t('common.delete')}
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
        ) : (
          <EmptyState title={t('states.emptyTitle')} message={t('tasks.noTasks')} />
        )}
      </Panel>
    </div>
  );
}
