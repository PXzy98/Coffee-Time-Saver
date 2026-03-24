import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { getApiErrorMessage } from '../api/client';
import { listProjects } from '../api/projects';
import { downloadRiskReport, getRiskReport, getRiskStatus, listTools, runRiskAnalysis } from '../api/tools';
import { EmptyState, ErrorState, LoadingState } from '../components/common/PageState';
import { Panel } from '../components/common/Panel';
import { RiskReportView } from '../components/tools/RiskReportView';
import { useWsEvent } from '../hooks/useWsEvent';
import { useUiStore } from '../store/uiStore';
import type { ProjectOut, RiskReport, RunStatusResponse, ToolRegistryItem } from '../types';

export function ToolsPage() {
  const { t } = useTranslation();
  const locale = useUiStore((state) => state.language);
  const pushToast = useUiStore((state) => state.pushToast);

  const [tools, setTools] = useState<ToolRegistryItem[]>([]);
  const [projects, setProjects] = useState<ProjectOut[]>([]);
  const [selectedToolSlug, setSelectedToolSlug] = useState<string | null>(null);
  const [selectedProjectId, setSelectedProjectId] = useState('');
  const [includeWebSearch, setIncludeWebSearch] = useState(false);
  const [runStatus, setRunStatus] = useState<RunStatusResponse | null>(null);
  const [report, setReport] = useState<RiskReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [downloadingFormat, setDownloadingFormat] = useState<'pdf' | 'docx' | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const selectedTool = useMemo(
    () => tools.find((tool) => tool.slug === selectedToolSlug) ?? null,
    [selectedToolSlug, tools],
  );

  const currentReportId = runStatus?.report_id ?? null;

  const loadData = useCallback(async () => {
    setErrorMessage(null);
    try {
      const [toolData, projectData] = await Promise.all([listTools(), listProjects()]);
      setTools(toolData);
      setProjects(projectData);
      if (!selectedToolSlug && toolData.length) {
        setSelectedToolSlug(toolData[0].slug);
      }
    } catch (error) {
      setErrorMessage(getApiErrorMessage(error));
    } finally {
      setLoading(false);
    }
  }, [selectedToolSlug]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const refreshReport = useCallback(
    async (reportId: string) => {
      try {
        const status = await getRiskStatus(reportId);
        setRunStatus(status);
        if (status.status === 'completed') {
          const loadedReport = await getRiskReport(reportId);
          setReport(loadedReport);
          setRunning(false);
        }
        if (status.status === 'failed') {
          setRunning(false);
        }
      } catch (error) {
        setErrorMessage(getApiErrorMessage(error));
        setRunning(false);
      }
    },
    [],
  );

  useEffect(() => {
    if (!currentReportId || runStatus?.status !== 'running') {
      return;
    }

    const timer = window.setInterval(() => {
      void refreshReport(currentReportId);
    }, 3000);

    return () => {
      window.clearInterval(timer);
    };
  }, [currentReportId, refreshReport, runStatus?.status]);

  useWsEvent(
    useCallback(
      (event) => {
        if (event.type !== 'tool.risk_analyzer.completed') {
          return;
        }

        const payload = event.payload as { report_id?: string };
        if (payload.report_id && payload.report_id === currentReportId) {
          void refreshReport(payload.report_id);
        }
      },
      [currentReportId, refreshReport],
    ),
  );

  async function handleRunAnalysis(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedProjectId) {
      pushToast({
        tone: 'warning',
        title: 'Select a project first',
      });
      return;
    }

    setRunning(true);
    setReport(null);
    setErrorMessage(null);
    try {
      const status = await runRiskAnalysis({
        project_id: selectedProjectId,
        include_web_search: includeWebSearch,
      });
      setRunStatus(status);
    } catch (error) {
      setRunning(false);
      setErrorMessage(getApiErrorMessage(error));
    }
  }

  async function handleDownload(format: 'pdf' | 'docx') {
    if (!currentReportId) {
      return;
    }

    setDownloadingFormat(format);
    try {
      const blob = await downloadRiskReport(currentReportId, format);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `risk_report_${currentReportId}.${format}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (error) {
      pushToast({
        tone: 'error',
        title: t('states.errorTitle'),
        message: getApiErrorMessage(error),
      });
    } finally {
      setDownloadingFormat(null);
    }
  }

  return (
    <div className="page-stack">
      <header className="page-header">
        <div>
          <h1>{t('tools.title')}</h1>
          <p>{t('tools.subtitle')}</p>
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
          <div className="tool-grid">
            {tools.map((tool) => {
              const localizedName = locale === 'fr' ? tool.name_fr : tool.name_en;
              const localizedDescription = locale === 'fr' ? tool.description_fr : tool.description_en;
              return (
                <button
                  key={tool.slug}
                  type="button"
                  className={`tool-card${selectedToolSlug === tool.slug ? ' tool-card-selected' : ''}`}
                  onClick={() => setSelectedToolSlug(tool.slug)}
                >
                  <p className="eyebrow">{tool.icon ?? 'module'}</p>
                  <h3>{localizedName}</h3>
                  <p>{localizedDescription}</p>
                </button>
              );
            })}
          </div>

          {selectedTool?.slug === 'risk-analyzer' ? (
            <Panel title={locale === 'fr' ? selectedTool.name_fr : selectedTool.name_en}>
              <div className="tool-layout">
                <form className="form-grid padded-form tool-form" onSubmit={handleRunAnalysis}>
                  <label className="field">
                    <span>{t('tasks.project')}</span>
                    <select value={selectedProjectId} onChange={(event) => setSelectedProjectId(event.target.value)} required>
                      <option value="">Select project</option>
                      {projects.map((project) => (
                        <option key={project.id} value={project.id}>
                          {project.name}
                        </option>
                      ))}
                    </select>
                  </label>

                  <label className="checkbox-field">
                    <input
                      type="checkbox"
                      checked={includeWebSearch}
                      onChange={(event) => setIncludeWebSearch(event.target.checked)}
                    />
                    <span>{t('tools.includeWebSearch')}</span>
                  </label>

                  <div className="form-actions">
                    <button type="submit" className="primary-button" disabled={running}>
                      {running ? t('common.loading') : t('tools.runAnalysis')}
                    </button>
                  </div>

                  <div className="status-box">
                    <p className="status-box-label">{t('tools.reportStatus')}</p>
                    <strong>{runStatus?.status ?? 'idle'}</strong>
                    {runStatus?.message ? <p className="helper-text">{runStatus.message}</p> : null}
                  </div>
                </form>

                <div className="tool-results">
                  {report ? (
                    <RiskReportView report={report} onDownload={handleDownload} downloadingFormat={downloadingFormat} />
                  ) : currentReportId ? (
                    <EmptyState
                      title={runStatus?.status === 'failed' ? t('states.errorTitle') : t('common.loading')}
                      message={runStatus?.message ?? `Report ${currentReportId} is still ${runStatus?.status ?? 'pending'}.`}
                    />
                  ) : (
                    <EmptyState title={t('states.emptyTitle')} message="Run the analyzer to populate this panel." />
                  )}
                </div>
              </div>
            </Panel>
          ) : selectedTool ? (
            <Panel title={locale === 'fr' ? selectedTool.name_fr : selectedTool.name_en}>
              <div className="state-card">
                <p>{locale === 'fr' ? selectedTool.description_fr : selectedTool.description_en}</p>
                <p className="helper-text">{t('tools.notExecutable')}</p>
              </div>
            </Panel>
          ) : (
            <EmptyState title={t('states.emptyTitle')} message="No enabled tools found." />
          )}
        </>
      ) : null}
    </div>
  );
}
