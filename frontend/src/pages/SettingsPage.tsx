import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { getApiErrorMessage } from '../api/client';
import { listProjects, toggleProjectShare } from '../api/projects';
import {
  createLlmConfig,
  getEmailConfig,
  listLlmConfigs,
  listUsers,
  testLlmConfigById,
  updateEmailConfig,
  updateLlmConfig,
  updateUserRoles,
} from '../api/settings';
import { EmptyState, ErrorState, LoadingState } from '../components/common/PageState';
import { Panel } from '../components/common/Panel';
import { isAdmin, useAuthStore } from '../store/authStore';
import { useUiStore } from '../store/uiStore';
import type { EmailBotConfigOut, LLMConfigCreate, LLMConfigOut, LLMConfigUpdate, ProjectOut, UserAdminOut } from '../types';

type SettingsTab = 'profile' | 'llm' | 'email' | 'projects' | 'users';

const availableRoles = ['admin', 'pm'];

export function SettingsPage() {
  const { t } = useTranslation();
  const user = useAuthStore((state) => state.user);
  const language = useUiStore((state) => state.language);
  const pushToast = useUiStore((state) => state.pushToast);

  const [activeTab, setActiveTab] = useState<SettingsTab>('profile');
  const [llmConfigs, setLlmConfigs] = useState<LLMConfigOut[]>([]);
  const [llmApiKeys, setLlmApiKeys] = useState<Record<number, string>>({});
  const [selectedActiveId, setSelectedActiveId] = useState<number | ''>('');
  const [showAddLlm, setShowAddLlm] = useState(false);
  const [newLlm, setNewLlm] = useState<LLMConfigCreate>({ name: 'primary', provider: 'openai', api_url: '', api_key: '', model: '', is_active: false });
  const [emailConfig, setEmailConfig] = useState<EmailBotConfigOut | null>(null);
  const [projects, setProjects] = useState<ProjectOut[]>([]);
  const [users, setUsers] = useState<UserAdminOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [busyKey, setBusyKey] = useState<string | null>(null);

  const admin = isAdmin(user);

  const tabs = useMemo<SettingsTab[]>(
    () => (admin ? ['profile', 'llm', 'email', 'projects', 'users'] : ['profile']),
    [admin],
  );

  const loadData = useCallback(async () => {
    setErrorMessage(null);
    try {
      if (!admin) {
        setLoading(false);
        return;
      }

      const [llmData, emailData, projectData, userData] = await Promise.all([
        listLlmConfigs(),
        getEmailConfig(),
        listProjects(),
        listUsers(),
      ]);
      setLlmConfigs(llmData);
      const activeConfig = llmData.find((c) => c.is_active);
      setSelectedActiveId(activeConfig ? activeConfig.id : '');
      setEmailConfig(emailData);
      setProjects(projectData);
      setUsers(userData);
    } catch (error) {
      setErrorMessage(getApiErrorMessage(error));
    } finally {
      setLoading(false);
    }
  }, [admin]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  async function handleSetActive() {
    if (selectedActiveId === '') return;
    setBusyKey('set-active');
    try {
      const updated = await updateLlmConfig(selectedActiveId, { is_active: true });
      setLlmConfigs((current) =>
        current.map((item) => ({ ...item, is_active: item.id === updated.id })),
      );
      pushToast({ tone: 'success', title: `${updated.name} set as active model` });
    } catch (error) {
      pushToast({ tone: 'error', title: t('states.errorTitle'), message: getApiErrorMessage(error) });
    } finally {
      setBusyKey(null);
    }
  }

  async function handleSaveLlm(config: LLMConfigOut) {
    setBusyKey(`llm-${config.id}`);
    try {
      const payload: LLMConfigUpdate = {
        provider: config.provider,
        api_url: config.api_url,
        model: config.model,
      };
      const keyVal = llmApiKeys[config.id];
      if (keyVal) {
        payload.api_key = keyVal;
      }
      const updated = await updateLlmConfig(config.id, payload);
      setLlmConfigs((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      setLlmApiKeys((current) => { const next = { ...current }; delete next[config.id]; return next; });
      pushToast({ tone: 'success', title: `${config.name} saved` });
    } catch (error) {
      pushToast({ tone: 'error', title: t('states.errorTitle'), message: getApiErrorMessage(error) });
    } finally {
      setBusyKey(null);
    }
  }

  async function handleAddLlm() {
    setBusyKey('add-llm');
    try {
      const created = await createLlmConfig(newLlm);
      setLlmConfigs((current) => [...current, created]);
      setShowAddLlm(false);
      setNewLlm({ name: 'primary', provider: 'openai', api_url: '', api_key: '', model: '', is_active: true });
      pushToast({ tone: 'success', title: `${created.name} created` });
    } catch (error) {
      pushToast({ tone: 'error', title: t('states.errorTitle'), message: getApiErrorMessage(error) });
    } finally {
      setBusyKey(null);
    }
  }

  async function handleTestLlm(config: LLMConfigOut) {
    setBusyKey(`test-${config.id}`);
    try {
      const result = await testLlmConfigById(config.id);
      pushToast({
        tone: result.status === 'ok' ? 'success' : 'warning',
        title: `${config.name} ${result.status}`,
        message: result.response ?? result.detail,
      });
    } catch (error) {
      pushToast({ tone: 'error', title: t('states.errorTitle'), message: getApiErrorMessage(error) });
    } finally {
      setBusyKey(null);
    }
  }

  async function handleSaveEmail() {
    if (!emailConfig) {
      return;
    }

    setBusyKey('email');
    try {
      const response = await updateEmailConfig(emailConfig);
      pushToast({ tone: 'success', title: response.detail });
    } catch (error) {
      pushToast({ tone: 'error', title: t('states.errorTitle'), message: getApiErrorMessage(error) });
    } finally {
      setBusyKey(null);
    }
  }

  async function handleToggleProject(projectId: string, isShared: boolean) {
    setBusyKey(`project-${projectId}`);
    try {
      const updated = await toggleProjectShare(projectId, !isShared);
      setProjects((current) => current.map((project) => (project.id === updated.id ? updated : project)));
    } catch (error) {
      pushToast({ tone: 'error', title: t('states.errorTitle'), message: getApiErrorMessage(error) });
    } finally {
      setBusyKey(null);
    }
  }

  async function handleSaveUser(userItem: UserAdminOut) {
    setBusyKey(`user-${userItem.id}`);
    try {
      const updated = await updateUserRoles(userItem.id, {
        roles: userItem.roles,
      });
      setUsers((current) => current.map((entry) => (entry.id === updated.id ? updated : entry)));
      pushToast({ tone: 'success', title: `${userItem.email} updated` });
    } catch (error) {
      pushToast({ tone: 'error', title: t('states.errorTitle'), message: getApiErrorMessage(error) });
    } finally {
      setBusyKey(null);
    }
  }

  return (
    <div className="page-stack">
      <header className="page-header">
        <div>
          <h1>{t('settings.title')}</h1>
          <p>{t('settings.subtitle')}</p>
        </div>
      </header>

      <div className="tab-row">
        {tabs.map((tab) => (
          <button
            key={tab}
            type="button"
            className={`tab-button${activeTab === tab ? ' tab-button-active' : ''}`}
            onClick={() => setActiveTab(tab)}
          >
            {t(`settings.${tab === 'projects' ? 'projectVisibility' : tab}`)}
          </button>
        ))}
      </div>

      {loading ? <LoadingState title={t('common.loading')} /> : null}

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

      {!loading && !errorMessage && activeTab === 'profile' ? (
        <Panel title={t('settings.profile')}>
          <div className="detail-list padded-panel">
            <div>
              <span>{t('topbar.profile')}</span>
              <strong>{user?.display_name}</strong>
            </div>
            <div>
              <span>{t('auth.email')}</span>
              <strong>{user?.email}</strong>
            </div>
            <div>
              <span>{t('common.language')}</span>
              <strong>
                UI {language.toUpperCase()} / backend {user?.preferred_lang.toUpperCase()}
              </strong>
            </div>
            <div>
              <span>Roles</span>
              <strong>{user?.roles.join(', ')}</strong>
            </div>
          </div>
          <div className="panel-body padded-panel">
            <p className="helper-text">{t('settings.profileReadOnly')}</p>
          </div>
        </Panel>
      ) : null}

      {!loading && !errorMessage && admin && activeTab === 'llm' ? (
        <Panel title={t('settings.llm')}>
          <div className="settings-stack padded-panel">
            {llmConfigs.length > 0 && (
              <div className="active-model-selector">
                <label className="field">
                  <span>Active Model</span>
                  <div className="selector-row">
                    <select
                      value={selectedActiveId}
                      onChange={(e) => setSelectedActiveId(e.target.value ? Number(e.target.value) : '')}
                    >
                      <option value="">-- Select active model --</option>
                      {llmConfigs.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.name} ({c.provider} / {c.model})
                        </option>
                      ))}
                    </select>
                    <button
                      type="button"
                      className="primary-button"
                      onClick={() => void handleSetActive()}
                      disabled={busyKey === 'set-active' || selectedActiveId === ''}
                    >
                      Confirm
                    </button>
                  </div>
                </label>
              </div>
            )}

            {llmConfigs.map((config) => (
              <article key={config.id} className={`list-card${config.is_active ? ' list-card-active' : ''}`}>
                <div className="three-column-grid">
                  <label className="field">
                    <span>Name</span>
                    <input value={config.name} disabled />
                  </label>
                  <label className="field">
                    <span>Provider</span>
                    <input
                      value={config.provider}
                      onChange={(event) =>
                        setLlmConfigs((current) =>
                          current.map((item) =>
                            item.id === config.id ? { ...item, provider: event.target.value } : item,
                          ),
                        )
                      }
                    />
                  </label>
                  <label className="field">
                    <span>Model</span>
                    <input
                      value={config.model}
                      onChange={(event) =>
                        setLlmConfigs((current) =>
                          current.map((item) =>
                            item.id === config.id ? { ...item, model: event.target.value } : item,
                          ),
                        )
                      }
                    />
                  </label>
                </div>

                <label className="field">
                  <span>API URL</span>
                  <input
                    value={config.api_url}
                    onChange={(event) =>
                      setLlmConfigs((current) =>
                        current.map((item) =>
                          item.id === config.id ? { ...item, api_url: event.target.value } : item,
                        ),
                      )
                    }
                  />
                </label>

                <label className="field">
                  <span>API Key</span>
                  <input
                    type="password"
                    placeholder="Enter new key to update"
                    value={llmApiKeys[config.id] ?? ''}
                    onChange={(event) =>
                      setLlmApiKeys((current) => ({ ...current, [config.id]: event.target.value }))
                    }
                  />
                </label>

                {config.is_active && <span className="badge badge-low">Active</span>}

                <div className="form-actions">
                  <button
                    type="button"
                    className="primary-button"
                    onClick={() => void handleSaveLlm(config)}
                    disabled={busyKey === `llm-${config.id}`}
                  >
                    {t('common.save')}
                  </button>
                  <button
                    type="button"
                    className="secondary-button"
                    onClick={() => void handleTestLlm(config)}
                    disabled={busyKey === `test-${config.id}`}
                  >
                    Test
                  </button>
                </div>
              </article>
            ))}

            {!llmConfigs.length && !showAddLlm ? (
              <EmptyState title={t('states.emptyTitle')} message="No LLM configs yet. Add one to enable AI features." />
            ) : null}

            {showAddLlm ? (
              <article className="list-card">
                <div className="three-column-grid">
                  <label className="field">
                    <span>Name</span>
                    <input value={newLlm.name} onChange={(e) => setNewLlm({ ...newLlm, name: e.target.value })} />
                  </label>
                  <label className="field">
                    <span>Provider</span>
                    <select value={newLlm.provider} onChange={(e) => setNewLlm({ ...newLlm, provider: e.target.value })}>
                      <option value="openai">openai</option>
                      <option value="claude">claude</option>
                      <option value="ollama">ollama</option>
                    </select>
                  </label>
                  <label className="field">
                    <span>Model</span>
                    <input placeholder="e.g. google/gemini-2.5-flash" value={newLlm.model} onChange={(e) => setNewLlm({ ...newLlm, model: e.target.value })} />
                  </label>
                </div>
                <label className="field">
                  <span>API URL</span>
                  <input placeholder="e.g. https://openrouter.ai/api/v1" value={newLlm.api_url} onChange={(e) => setNewLlm({ ...newLlm, api_url: e.target.value })} />
                </label>
                <label className="field">
                  <span>API Key</span>
                  <input type="password" placeholder="sk-or-..." value={newLlm.api_key ?? ''} onChange={(e) => setNewLlm({ ...newLlm, api_key: e.target.value })} />
                </label>
                <div className="form-actions">
                  <button type="button" className="primary-button" onClick={() => void handleAddLlm()} disabled={busyKey === 'add-llm'}>
                    Create
                  </button>
                  <button type="button" className="ghost-button" onClick={() => setShowAddLlm(false)}>
                    Cancel
                  </button>
                </div>
              </article>
            ) : (
              <button type="button" className="secondary-button" onClick={() => setShowAddLlm(true)}>
                + Add LLM Config
              </button>
            )}
          </div>
        </Panel>
      ) : null}

      {!loading && !errorMessage && admin && activeTab === 'email' ? (
        <Panel title={t('settings.email')}>
          {emailConfig ? (
            <div className="form-grid padded-form">
              <div className="two-column-grid">
                <label className="field">
                  <span>Host</span>
                  <input
                    value={emailConfig.imap_host}
                    onChange={(event) => setEmailConfig((current) => (current ? { ...current, imap_host: event.target.value } : current))}
                  />
                </label>
                <label className="field">
                  <span>Port</span>
                  <input
                    type="number"
                    value={emailConfig.imap_port}
                    onChange={(event) =>
                      setEmailConfig((current) => (current ? { ...current, imap_port: Number(event.target.value) } : current))
                    }
                  />
                </label>
              </div>

              <div className="two-column-grid">
                <label className="field">
                  <span>User</span>
                  <input
                    value={emailConfig.imap_user}
                    onChange={(event) => setEmailConfig((current) => (current ? { ...current, imap_user: event.target.value } : current))}
                  />
                </label>
                <label className="field">
                  <span>Folder</span>
                  <input
                    value={emailConfig.imap_folder}
                    onChange={(event) => setEmailConfig((current) => (current ? { ...current, imap_folder: event.target.value } : current))}
                  />
                </label>
              </div>

              <label className="field">
                <span>Polling interval</span>
                <input
                  type="number"
                  value={emailConfig.poll_interval_seconds}
                  onChange={(event) =>
                    setEmailConfig((current) =>
                      current ? { ...current, poll_interval_seconds: Number(event.target.value) } : current,
                    )
                  }
                />
              </label>

              <div className="form-actions">
                <button type="button" className="primary-button" onClick={() => void handleSaveEmail()} disabled={busyKey === 'email'}>
                  {t('common.save')}
                </button>
              </div>

              <p className="helper-text">{t('settings.emailRestartNote')}</p>
            </div>
          ) : (
            <EmptyState title={t('states.emptyTitle')} message="No email config found." />
          )}
        </Panel>
      ) : null}

      {!loading && !errorMessage && admin && activeTab === 'projects' ? (
        <Panel title={t('settings.projectVisibility')}>
          <div className="settings-stack padded-panel">
            <p className="helper-text">Current backend only returns projects visible to this admin account.</p>
            {projects.length ? (
              projects.map((project) => (
                <article key={project.id} className="table-row">
                  <div>
                    <h3>{project.name}</h3>
                    <p>{project.description || 'No description'}</p>
                  </div>
                  <button
                    type="button"
                    className="secondary-button"
                    onClick={() => void handleToggleProject(project.id, project.is_shared)}
                    disabled={busyKey === `project-${project.id}`}
                  >
                    {project.is_shared ? 'Shared' : 'Private'}
                  </button>
                </article>
              ))
            ) : (
              <EmptyState title={t('states.emptyTitle')} message="No projects visible to this account." />
            )}
          </div>
        </Panel>
      ) : null}

      {!loading && !errorMessage && admin && activeTab === 'users' ? (
        <Panel title={t('settings.users')}>
          <div className="settings-stack padded-panel">
            {users.length ? (
              users.map((userItem) => (
                <article key={userItem.id} className="list-card">
                  <div className="task-title-row">
                    <div>
                      <h3>{userItem.display_name}</h3>
                      <p>{userItem.email}</p>
                    </div>
                    <span className={`badge ${userItem.is_active ? 'badge-medium' : 'badge-high'}`}>
                      {userItem.is_active ? 'active' : 'inactive'}
                    </span>
                  </div>

                  <div className="tag-cloud">
                    {availableRoles.map((role) => {
                      const checked = userItem.roles.includes(role);
                      return (
                        <label key={role} className="checkbox-field checkbox-tag">
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={(event) =>
                              setUsers((current) =>
                                current.map((entry) => {
                                  if (entry.id !== userItem.id) {
                                    return entry;
                                  }
                                  const nextRoles = event.target.checked
                                    ? [...entry.roles, role]
                                    : entry.roles.filter((item) => item !== role);
                                  return { ...entry, roles: Array.from(new Set(nextRoles)) };
                                }),
                              )
                            }
                          />
                          <span>{role}</span>
                        </label>
                      );
                    })}
                  </div>

                  <div className="form-actions">
                    <button
                      type="button"
                      className="primary-button"
                      onClick={() => void handleSaveUser(userItem)}
                      disabled={busyKey === `user-${userItem.id}`}
                    >
                      {t('common.save')}
                    </button>
                  </div>
                </article>
              ))
            ) : (
              <EmptyState title={t('states.emptyTitle')} message="No users available." />
            )}
          </div>
        </Panel>
      ) : null}
    </div>
  );
}
