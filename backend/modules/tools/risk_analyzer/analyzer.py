"""
All risk analysis logic lives here — one self-contained file.
Functions: gather_project_data → risk_modelling → inconsistency_detection → generate_report
To iterate on the approach, only this file needs to change.
"""
import json
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from core.models import Document, DocumentChunk, Email, Task, Project
from modules.llm_gateway.service import LLMGateway
from modules.llm_gateway.schemas import LLMRequest, Message
from modules.tools.risk_analyzer.schemas import (
    RiskItem, InconsistencyItem, RiskReport, ProjectContext,
)

logger = logging.getLogger("coffee_time_saver")


async def gather_project_data(project_id: uuid.UUID, db: AsyncSession) -> ProjectContext:
    """Collect all documents, emails, tasks for a project."""
    # Project info
    proj_result = await db.execute(select(Project).where(Project.id == project_id))
    project = proj_result.scalar_one_or_none()
    if project is None:
        raise ValueError(f"Project {project_id} not found")

    # Documents with chunks
    docs_result = await db.execute(
        select(Document)
        .options(selectinload(Document.chunks))
        .where(Document.project_id == project_id, Document.status == "completed")
    )
    documents = docs_result.scalars().all()

    # Emails linked to project
    emails_result = await db.execute(
        select(Email).where(Email.project_id == project_id)
    )
    emails = emails_result.scalars().all()

    # Tasks
    tasks_result = await db.execute(
        select(Task).where(Task.project_id == project_id)
    )
    tasks = tasks_result.scalars().all()

    return ProjectContext(
        project_id=project_id,
        project_name=project.name,
        documents=[
            {
                "id": str(d.id),
                "filename": d.filename,
                "doc_type": d.doc_type,
                "full_text": (d.full_text or "")[:8000],  # truncate for LLM context
                "chunks": [{"text": c.content_text, "lang": c.content_lang} for c in d.chunks[:20]],
            }
            for d in documents
        ],
        emails=[
            {
                "id": str(e.id),
                "subject": e.subject,
                "body_text": (e.body_text or "")[:2000],
                "received_at": str(e.received_at),
            }
            for e in emails
        ],
        tasks=[
            {
                "id": str(t.id),
                "title": t.title,
                "description": t.description,
                "status": "completed" if t.is_completed else "pending",
            }
            for t in tasks
        ],
    )


async def risk_modelling(
    context: ProjectContext,
    llm: LLMGateway,
    web_search: bool = False,
) -> list[RiskItem]:
    """LLM-based risk identification from project materials."""
    context_summary = _build_context_summary(context)

    tools = None
    if web_search:
        tools = [{
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Search the web for industry risk benchmarks, vendor status, or regulatory updates.",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            },
        }]

    request = LLMRequest(
        messages=[
            Message(role="system", content=(
                "You are a senior project risk analyst. "
                "Analyze the following project context and identify risks. "
                "Return a JSON array of risk objects with fields: "
                "id (string), description, category (technical|schedule|resource|scope), "
                "likelihood (1-5), impact (1-5), confidence (0.0-1.0), "
                "source_documents (list of filenames), source_quotes (list of text excerpts), mitigation."
            )),
            Message(role="user", content=context_summary),
        ],
        config_name="primary",
        response_format="json",
        max_tokens=3000,
        tools=tools,
    )

    try:
        response = await llm.complete(request)
        data = json.loads(response.content)
        if isinstance(data, dict) and "risks" in data:
            data = data["risks"]
        risks = []
        for item in (data if isinstance(data, list) else []):
            likelihood = int(item.get("likelihood", 3))
            impact = int(item.get("impact", 3))
            risks.append(RiskItem(
                id=item.get("id", str(uuid.uuid4())[:8]),
                description=item.get("description", ""),
                category=item.get("category", "general"),
                likelihood=likelihood,
                impact=impact,
                risk_score=round((likelihood * impact) / 25.0, 2),
                confidence=float(item.get("confidence", 0.7)),
                source_documents=item.get("source_documents", []),
                source_quotes=item.get("source_quotes", []),
                mitigation=item.get("mitigation", ""),
            ))
        return risks
    except Exception as e:
        logger.error("Risk modelling failed: %s", e)
        return []


async def inconsistency_detection(
    context: ProjectContext,
    llm: LLMGateway,
) -> list[InconsistencyItem]:
    """Cross-compare all saved materials for inconsistencies."""
    if len(context.documents) < 2:
        return []

    # Build pairs of documents to compare
    doc_pairs = []
    for i, doc_a in enumerate(context.documents):
        for doc_b in context.documents[i + 1:]:
            doc_pairs.append((doc_a, doc_b))

    inconsistencies = []
    for doc_a, doc_b in doc_pairs[:10]:  # limit pairs to avoid excessive LLM calls
        request = LLMRequest(
            messages=[
                Message(role="system", content=(
                    "You are a document consistency analyst. "
                    "Compare these two document excerpts and identify contradictions, "
                    "scope drift, or gaps. Return JSON array with fields: "
                    "id, type (contradiction|drift|gap), document_a (filename), passage_a, "
                    "document_b (filename), passage_b, explanation, confidence (0.0-1.0), recommendation. "
                    "Return empty array [] if no inconsistencies found."
                )),
                Message(role="user", content=json.dumps({
                    "document_a": {"filename": doc_a["filename"], "type": doc_a["doc_type"], "text": doc_a["full_text"][:3000]},
                    "document_b": {"filename": doc_b["filename"], "type": doc_b["doc_type"], "text": doc_b["full_text"][:3000]},
                })),
            ],
            config_name="primary",
            response_format="json",
            max_tokens=2000,
        )
        try:
            response = await llm.complete(request)
            data = json.loads(response.content)
            if isinstance(data, dict) and "inconsistencies" in data:
                data = data["inconsistencies"]
            for item in (data if isinstance(data, list) else []):
                inconsistencies.append(InconsistencyItem(
                    id=item.get("id", str(uuid.uuid4())[:8]),
                    type=item.get("type", "contradiction"),
                    document_a=item.get("document_a", doc_a["filename"]),
                    passage_a=item.get("passage_a", ""),
                    document_b=item.get("document_b", doc_b["filename"]),
                    passage_b=item.get("passage_b", ""),
                    explanation=item.get("explanation", ""),
                    confidence=float(item.get("confidence", 0.6)),
                    recommendation=item.get("recommendation", ""),
                ))
        except Exception as e:
            logger.error("Inconsistency detection failed for pair (%s, %s): %s",
                         doc_a["filename"], doc_b["filename"], e)

    return inconsistencies


async def generate_report(
    project_id: uuid.UUID,
    risks: list[RiskItem],
    inconsistencies: list[InconsistencyItem],
    context: ProjectContext,
) -> RiskReport:
    """Combine all findings into final report with overall confidence."""
    all_confidences = [r.confidence for r in risks] + [i.confidence for i in inconsistencies]
    overall_confidence = round(sum(all_confidences) / len(all_confidences), 2) if all_confidences else 0.0

    max_risk_score = max((r.risk_score for r in risks), default=0.0)
    if max_risk_score >= 0.8:
        overall_risk_level = "critical"
    elif max_risk_score >= 0.6:
        overall_risk_level = "high"
    elif max_risk_score >= 0.4:
        overall_risk_level = "medium"
    else:
        overall_risk_level = "low"

    top_risks = sorted(risks, key=lambda r: r.risk_score, reverse=True)[:3]
    exec_summary_parts = [
        f"Project '{context.project_name}' analysis identified {len(risks)} risk(s) "
        f"and {len(inconsistencies)} inconsistency/inconsistencies.",
    ]
    if top_risks:
        exec_summary_parts.append(
            "Top risks: " + "; ".join(r.description[:80] for r in top_risks) + "."
        )

    return RiskReport(
        report_id=uuid.uuid4(),
        project_id=project_id,
        generated_at=datetime.now(timezone.utc),
        overall_risk_level=overall_risk_level,
        overall_confidence=overall_confidence,
        executive_summary=" ".join(exec_summary_parts),
        risks=risks,
        inconsistencies=inconsistencies,
        documents_analyzed=[d["filename"] for d in context.documents],
        methodology_notes=(
            "Phase 1: LLM-based risk identification from project documents, emails, and tasks. "
            "Phase 2: Cross-document inconsistency detection via pairwise LLM comparison. "
            "Confidence scores are LLM self-reported estimates."
        ),
    )


async def run_full_analysis(
    project_id: uuid.UUID,
    db: AsyncSession,
    llm: LLMGateway,
    web_search: bool = False,
) -> RiskReport:
    """Main entry point. Orchestrates all steps sequentially."""
    context = await gather_project_data(project_id, db)
    risks = await risk_modelling(context, llm, web_search)
    inconsistencies = await inconsistency_detection(context, llm)
    return await generate_report(project_id, risks, inconsistencies, context)


def _build_context_summary(context: ProjectContext) -> str:
    parts = [f"Project: {context.project_name}\n"]
    parts.append(f"Documents ({len(context.documents)}):")
    for doc in context.documents[:5]:
        parts.append(f"  [{doc['doc_type']}] {doc['filename']}: {doc['full_text'][:500]}...")
    parts.append(f"\nEmails ({len(context.emails)}):")
    for em in context.emails[:3]:
        parts.append(f"  Subject: {em['subject']} — {em['body_text'][:200]}...")
    parts.append(f"\nTasks ({len(context.tasks)}):")
    for t in context.tasks[:10]:
        parts.append(f"  [{t['status']}] {t['title']}")
    return "\n".join(parts)
