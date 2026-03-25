import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class RiskAnalyzerRunRequest(BaseModel):
    project_id: uuid.UUID
    include_web_search: bool = False


class RiskItem(BaseModel):
    id: str
    title: str = ""
    description: str
    category: str                    # technical, schedule, resource, scope, security, compliance
    likelihood: int                  # 1-5
    impact: int                      # 1-5
    probability_label: str = ""      # Low / Medium / High
    impact_label: str = ""           # Low / Medium / High
    risk_score: float                # likelihood × impact, normalized 0-1
    confidence: float                # 0.0 - 1.0
    affected_area: str = ""
    source_documents: list[str]
    source_quotes: list[str]
    mitigation: str                  # legacy single string
    mitigation_strategies: list[str] = []  # structured list matching BC format


class InconsistencyItem(BaseModel):
    id: str
    type: str  # contradiction, drift, gap
    document_a: str
    passage_a: str
    document_b: str
    passage_b: str
    explanation: str
    confidence: float  # 0.0 - 1.0
    recommendation: str


class RiskReport(BaseModel):
    report_id: uuid.UUID
    project_id: uuid.UUID
    generated_at: datetime
    overall_risk_level: str  # low, medium, high, critical
    overall_confidence: float
    executive_summary: str
    risks: list[RiskItem]
    inconsistencies: list[InconsistencyItem]
    documents_analyzed: list[str]
    methodology_notes: str


class ProjectContext(BaseModel):
    project_id: uuid.UUID
    project_name: str
    documents: list[dict]  # {id, filename, doc_type, full_text, chunks: [{text, lang}]}
    emails: list[dict]     # {id, subject, body_text, received_at}
    tasks: list[dict]      # {id, title, description, status}


class RunStatusResponse(BaseModel):
    report_id: Optional[uuid.UUID]
    status: str  # pending, running, completed, failed
    message: Optional[str] = None
