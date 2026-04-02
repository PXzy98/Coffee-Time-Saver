import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class RiskAnalyzerRunRequest(BaseModel):
    project_id: uuid.UUID
    include_web_search: bool = Field(
        default=False,
        deprecated=True,
        description="Deprecated — web search is not implemented. This field is ignored.",
    )
    use_full_text: bool = Field(
        default=False,
        description="Skip chunk summarization and use the raw full_text of each document directly for analysis.",
    )


# ---------------------------------------------------------------------------
# Layered summarization intermediate models (in-memory only, not persisted)
# ---------------------------------------------------------------------------

class ChunkSummary(BaseModel):
    chunk_id: str
    document_id: str
    chunk_index: int
    summary: str              # ~50-100 words
    key_entities: list[str] = []   # people, systems, dates, amounts
    risk_signals: list[str] = []   # potential risk indicators
    topic: str = ""                # short topic label


class DocumentSummary(BaseModel):
    document_id: str
    filename: str
    doc_type: str
    summary: str              # ~200-400 words
    key_entities: list[str] = []
    risk_signals: list[str] = []
    commitments: list[str] = []    # promises, deadlines, deliverables
    chunk_count: int = 0


class EvidencePack(BaseModel):
    project_name: str
    document_summaries: list[DocumentSummary] = []
    email_evidence: list[dict] = []
    task_evidence: list[dict] = []
    total_chunks_analyzed: int = 0
    total_documents: int = 0
    total_emails: int = 0
    total_tasks: int = 0


# ---------------------------------------------------------------------------
# Risk and report models
# ---------------------------------------------------------------------------

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
    confidence: float                # 0.0 - 1.0 (LLM self-reported)
    adjusted_confidence: float = 0.0  # evidence-density adjusted confidence
    evidence_chunk_count: int = 0    # how many chunks contributed evidence
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
    source_chunk_ids: list[str] = []


class RiskReport(BaseModel):
    model_config = {"protected_namespaces": ()}

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
    model_name: str = ""  # LLM provider/model used for analysis
    warnings: list[str] = []  # degradation warnings from pipeline
    evidence_pack_stats: dict = {}  # {chunks_analyzed, docs, emails, tasks}


class ProjectContext(BaseModel):
    project_id: uuid.UUID
    project_name: str
    documents: list[dict]  # {id, filename, doc_type, full_text, chunks: [{id, text, lang, index}]}
    emails: list[dict]     # {id, subject, from_address, body_text, received_at}
    tasks: list[dict]      # {id, title, description, status, priority, due_date}


class RunStatusResponse(BaseModel):
    report_id: Optional[uuid.UUID]
    status: str  # pending, running, completed, failed
    message: Optional[str] = None
