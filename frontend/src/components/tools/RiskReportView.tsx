import type { RiskReport } from '../../types';

interface RiskReportViewProps {
  report: RiskReport;
  onDownload: (format: 'pdf' | 'docx') => void;
  downloadingFormat: 'pdf' | 'docx' | null;
}

export function RiskReportView({ report, onDownload, downloadingFormat }: RiskReportViewProps) {
  return (
    <div className="tool-report">
      <div className="tool-report-header">
        <div>
          <p className="eyebrow">Report</p>
          <h3>{report.overall_risk_level.toUpperCase()}</h3>
          <p>{report.executive_summary}</p>
        </div>
        <div className="tool-report-actions">
          <button
            type="button"
            className="secondary-button"
            onClick={() => onDownload('pdf')}
            disabled={Boolean(downloadingFormat)}
          >
            {downloadingFormat === 'pdf' ? 'Downloading…' : 'PDF'}
          </button>
          <button
            type="button"
            className="secondary-button"
            onClick={() => onDownload('docx')}
            disabled={Boolean(downloadingFormat)}
          >
            {downloadingFormat === 'docx' ? 'Downloading…' : 'DOCX'}
          </button>
        </div>
      </div>

      <div className="tool-summary-grid">
        <article className="metric-card metric-card-accent">
          <p className="metric-label">Confidence</p>
          <p className="metric-value">{Math.round(report.overall_confidence * 100)}%</p>
        </article>
        <article className="metric-card metric-card-warm">
          <p className="metric-label">Documents</p>
          <p className="metric-value">{report.documents_analyzed.length}</p>
        </article>
        <article className="metric-card metric-card-danger">
          <p className="metric-label">Risks</p>
          <p className="metric-value">{report.risks.length}</p>
        </article>
      </div>

      <div className="tool-section">
        <h4>Risks</h4>
        <div className="card-list">
          {report.risks.map((risk) => (
            <article key={risk.id} className="list-card">
              <div className="task-title-row">
                <h5>{risk.description}</h5>
                <span className="badge badge-high">{Math.round(risk.risk_score * 100)}%</span>
              </div>
              <p className="task-description">{risk.mitigation}</p>
              <div className="task-meta">
                <span>{risk.category}</span>
                <span>Likelihood {risk.likelihood}</span>
                <span>Impact {risk.impact}</span>
              </div>
            </article>
          ))}
        </div>
      </div>

      <div className="tool-section">
        <h4>Inconsistencies</h4>
        <div className="card-list">
          {report.inconsistencies.map((item) => (
            <article key={item.id} className="list-card">
              <div className="task-title-row">
                <h5>{item.type}</h5>
                <span className="badge badge-medium">{Math.round(item.confidence * 100)}%</span>
              </div>
              <p className="task-description">{item.explanation}</p>
              <p className="helper-text">{item.recommendation}</p>
            </article>
          ))}
        </div>
      </div>
    </div>
  );
}
