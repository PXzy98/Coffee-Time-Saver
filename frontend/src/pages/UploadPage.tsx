import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { getApiErrorMessage } from '../api/client';
import { getFileStatus, listFiles, uploadSingleFile } from '../api/files';
import { listProjects } from '../api/projects';
import { EmptyState, ErrorState, LoadingState } from '../components/common/PageState';
import { Panel } from '../components/common/Panel';
import { useWsEvent } from '../hooks/useWsEvent';
import { useUiStore } from '../store/uiStore';
import type { DocumentOut, ProjectOut } from '../types';
import { formatDate } from '../utils/format';

interface UploadQueueItem {
  id: string;
  file: File;
  progress: number;
  status: 'selected' | 'uploading' | 'pending' | 'processing' | 'completed' | 'failed';
  documentId?: string;
  error?: string;
}

function makeQueueId(file: File): string {
  return `${file.name}-${file.lastModified}-${file.size}`;
}

export function UploadPage() {
  const { t } = useTranslation();
  const locale = useUiStore((state) => state.language);
  const pushToast = useUiStore((state) => state.pushToast);
  const inputRef = useRef<HTMLInputElement | null>(null);

  const [projects, setProjects] = useState<ProjectOut[]>([]);
  const [documents, setDocuments] = useState<DocumentOut[]>([]);
  const [queue, setQueue] = useState<UploadQueueItem[]>([]);
  const [projectId, setProjectId] = useState('');
  const [docType, setDocType] = useState('general');
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const activeQueueItems = useMemo(
    () => queue.filter((item) => item.documentId && !['completed', 'failed'].includes(item.status)),
    [queue],
  );

  const loadData = useCallback(async () => {
    setErrorMessage(null);
    try {
      const [projectData, documentData] = await Promise.all([listProjects(), listFiles()]);
      setProjects(projectData);
      setDocuments(documentData);
    } catch (error) {
      setErrorMessage(getApiErrorMessage(error));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  useEffect(() => {
    if (!activeQueueItems.length) {
      return;
    }

    const timer = window.setInterval(() => {
      void Promise.all(
        activeQueueItems.map(async (item) => {
          if (!item.documentId) {
            return null;
          }
          const status = await getFileStatus(item.documentId);
          return { id: item.id, status: status.status };
        }),
      ).then((updates) => {
        const meaningfulUpdates = updates.filter(Boolean) as { id: string; status: UploadQueueItem['status'] }[];
        if (!meaningfulUpdates.length) {
          return;
        }

        setQueue((current) =>
          current.map((item) => {
            const update = meaningfulUpdates.find((entry) => entry.id === item.id);
            return update ? { ...item, status: update.status } : item;
          }),
        );

        if (meaningfulUpdates.some((update) => ['completed', 'failed'].includes(update.status))) {
          void loadData();
        }
      }).catch(() => {
        // Ignore polling jitter; the next pass or websocket event can recover.
      });
    }, 4000);

    return () => {
      window.clearInterval(timer);
    };
  }, [activeQueueItems, loadData]);

  useWsEvent(
    useCallback(
      (event) => {
        if (event.type !== 'file.status_changed') {
          return;
        }

        const payload = event.payload as { document_id?: string; status?: UploadQueueItem['status'] };
        const status = payload.status;
        if (!payload.document_id || !status) {
          return;
        }

        setQueue((current) =>
          current.map((item) =>
            item.documentId === payload.document_id ? { ...item, status } : item,
          ),
        );

        if (['completed', 'failed'].includes(status)) {
          void loadData();
        }
      },
      [loadData],
    ),
  );

  function addFiles(files: FileList | File[]) {
    const nextItems = Array.from(files).map((file) => ({
      id: makeQueueId(file),
      file,
      progress: 0,
      status: 'selected' as const,
    }));

    setQueue((current) => {
      const existingIds = new Set(current.map((item) => item.id));
      return [...current, ...nextItems.filter((item) => !existingIds.has(item.id))];
    });
  }

  async function handleStartUpload() {
    const pendingItems = queue.filter((item) => item.status === 'selected');
    if (!pendingItems.length) {
      pushToast({
        tone: 'warning',
        title: 'Choose at least one file first',
      });
      return;
    }

    setUploading(true);

    for (const item of pendingItems) {
      setQueue((current) =>
        current.map((entry) => (entry.id === item.id ? { ...entry, status: 'uploading', progress: 0 } : entry)),
      );

      try {
        const response = await uploadSingleFile({
          file: item.file,
          projectId: projectId || undefined,
          docType,
          onProgress: (progress) => {
            setQueue((current) =>
              current.map((entry) => (entry.id === item.id ? { ...entry, progress } : entry)),
            );
          },
        });

        setQueue((current) =>
          current.map((entry) =>
            entry.id === item.id
              ? {
                  ...entry,
                  progress: 100,
                  status: response.status as UploadQueueItem['status'],
                  documentId: response.document_id,
                }
              : entry,
          ),
        );
      } catch (error) {
        setQueue((current) =>
          current.map((entry) =>
            entry.id === item.id
              ? {
                  ...entry,
                  status: 'failed',
                  error: getApiErrorMessage(error),
                }
              : entry,
          ),
        );
      }
    }

    setUploading(false);
    await loadData();
  }

  return (
    <div className="page-stack">
      <header className="page-header">
        <div>
          <h1>{t('upload.title')}</h1>
          <p>{t('upload.subtitle')}</p>
        </div>
      </header>

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

      {!loading && !errorMessage ? (
        <>
          <Panel title={t('upload.queue')}>
            <div className="padded-panel upload-stack">
              <div
                className="dropzone"
                onClick={() => inputRef.current?.click()}
                onDragOver={(event) => {
                  event.preventDefault();
                }}
                onDrop={(event) => {
                  event.preventDefault();
                  addFiles(event.dataTransfer.files);
                }}
              >
                <input
                  ref={inputRef}
                  type="file"
                  multiple
                  className="hidden-input"
                  onChange={(event) => {
                    if (event.target.files) {
                      addFiles(event.target.files);
                    }
                  }}
                />
                <p>{t('upload.dropzone')}</p>
                <span className="helper-text">PDF, DOCX, XLSX, CSV, TXT, MD</span>
              </div>

              <div className="two-column-grid">
                <label className="field">
                  <span>{t('upload.project')}</span>
                  <select value={projectId} onChange={(event) => setProjectId(event.target.value)}>
                    <option value="">{t('tasks.allProjects')}</option>
                    {projects.map((project) => (
                      <option key={project.id} value={project.id}>
                        {project.name}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="field">
                  <span>{t('upload.documentType')}</span>
                  <input value={docType} onChange={(event) => setDocType(event.target.value)} />
                </label>
              </div>

              <div className="form-actions">
                <button type="button" className="primary-button" onClick={() => void handleStartUpload()} disabled={uploading}>
                  {uploading ? t('common.loading') : t('upload.startUpload')}
                </button>
              </div>

              {queue.length ? (
                <div className="upload-queue-list">
                  {queue.map((item) => (
                    <article key={item.id} className="upload-item">
                      <div className="upload-item-header">
                        <div>
                          <h3>{item.file.name}</h3>
                          <p>{item.documentId ?? 'local only'}</p>
                        </div>
                        <span className={`badge badge-${item.status === 'failed' ? 'high' : item.status === 'completed' ? 'medium' : 'low'}`}>
                          {item.status}
                        </span>
                      </div>
                      <div className="progress-track">
                        <div className="progress-bar" style={{ width: `${item.progress}%` }} />
                      </div>
                      {item.error ? <p className="error-text">{item.error}</p> : null}
                    </article>
                  ))}
                </div>
              ) : (
                <EmptyState title={t('states.emptyTitle')} message="No files staged yet." />
              )}
            </div>
          </Panel>

          <Panel title={t('upload.uploadedFiles')}>
            <div className="panel-body padded-panel">
              {documents.length ? (
                <div className="table-list">
                  {documents.map((document) => (
                    <article key={document.id} className="table-row">
                      <div>
                        <h3>{document.filename}</h3>
                        <p>{document.doc_type}</p>
                      </div>
                      <div className="table-row-meta">
                        <span>{document.status}</span>
                        <span>{formatDate(document.created_at, locale)}</span>
                      </div>
                    </article>
                  ))}
                </div>
              ) : (
                <EmptyState title={t('states.emptyTitle')} message={t('upload.noFiles')} />
              )}
            </div>
          </Panel>
        </>
      ) : null}
    </div>
  );
}
