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


import re


def _extract_json(raw: str) -> dict | list | None:
    """Robustly extract JSON from LLM output that may contain thinking/reasoning text."""
    raw = raw.strip()
    # 1. Strip markdown code fences: ```json ... ```
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)```", raw, re.DOTALL)
    if fence_match:
        raw = fence_match.group(1).strip()
    # 2. If still not valid JSON, find the first { or [ and last } or ]
    if raw and raw[0] not in ('{', '['):
        start = min(
            (raw.find(c) for c in ('{', '[') if raw.find(c) != -1),
            default=-1,
        )
        if start == -1:
            return None
        raw = raw[start:]
    if not raw:
        return None
    # Find matching end bracket
    open_char = raw[0]
    close_char = '}' if open_char == '{' else ']'
    end = raw.rfind(close_char)
    if end == -1:
        return None
    raw = raw[:end + 1]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


_LABEL_TO_INT = {"low": 2, "medium": 3, "high": 4, "critical": 5}
_INT_TO_LABEL = {1: "Low", 2: "Low", 3: "Medium", 4: "High", 5: "High"}


def _parse_label(val: str) -> int:
    return _LABEL_TO_INT.get(str(val).lower().strip(), 3)


async def risk_modelling(
    context: ProjectContext,
    llm: LLMGateway,
    web_search: bool = False,
) -> list[RiskItem]:
    """LLM-based risk identification from project materials."""
    context_summary = _build_context_summary(context)

    system_prompt = """You are a senior project risk analyst preparing a formal risk register for a government project gate review.

Analyze the project materials and identify ALL significant risks. For each risk, produce a structured entry matching a formal Business Case risk table.

Return a JSON object with key "risks" containing an array. Each risk object must have:
- "id": string like "RSK-1", "RSK-2", etc.
- "title": short risk title (max 8 words, e.g. "Procurement Timeline Delay")
- "description": full paragraph (2-4 sentences) describing the risk, its trigger, and potential consequence
- "category": one of: technical, schedule, resource, scope, security, compliance
- "probability": one of: Low, Medium, High
- "impact": one of: Low, Medium, High
- "affected_area": the project area most affected (e.g. "Deployment", "Data Migration", "Budget")
- "mitigation_strategies": array of 3-5 specific mitigation actions (each a full sentence)
- "source_documents": array of document filenames where evidence was found
- "source_quotes": array of 1-3 direct quotes from the source materials supporting this risk
- "confidence": float 0.0-1.0 (your confidence that this is a genuine risk based on evidence)

Only include risks with clear evidence in the provided materials. Do not invent risks."""

    request = LLMRequest(
        messages=[
            Message(role="system", content=system_prompt),
            Message(role="user", content=context_summary),
        ],
        config_name="primary",
        response_format="json",
        max_tokens=32000,   # thinking models need large budget: ~20k thinking + ~5k JSON output
        temperature=0.3,
    )

    # LLM call errors (auth, network, timeout) propagate — caller sets status=failed
    response = await llm.complete(request)
    logger.info("Risk modelling: LLM response length=%d, preview=%r",
                len(response.content), response.content[:300])

    # JSON parsing errors are non-fatal — log and return empty
    try:
        data = _extract_json(response.content)
        if data is None:
            logger.error("Risk modelling: failed to extract JSON — full response:\n%s", response.content[:2000])
            return []
        if isinstance(data, dict) and "risks" in data:
            data = data["risks"]
        risks = []
        for i, item in enumerate(data if isinstance(data, list) else []):
            prob = item.get("probability") or "Medium"
            imp = item.get("impact") or "Medium"
            likelihood = _parse_label(prob)
            impact = _parse_label(imp)
            strategies = item.get("mitigation_strategies") or []
            mitigation_text = "\n".join(f"- {s}" for s in strategies) if strategies else (item.get("mitigation") or "")
            risks.append(RiskItem(
                id=item.get("id") or f"RSK-{i+1}",
                title=item.get("title") or "",
                description=item.get("description") or "",
                category=item.get("category") or "general",
                likelihood=likelihood,
                impact=impact,
                probability_label=_INT_TO_LABEL.get(likelihood, "Medium"),
                impact_label=_INT_TO_LABEL.get(impact, "Medium"),
                risk_score=round((likelihood * impact) / 25.0, 2),
                confidence=float(item.get("confidence") or 0.7),
                affected_area=item.get("affected_area") or "",
                source_documents=item.get("source_documents") or [],
                source_quotes=item.get("source_quotes") or [],
                mitigation=mitigation_text,
                mitigation_strategies=strategies,
            ))
        return risks
    except Exception as e:
        logger.error("Risk modelling: JSON parse error: %s", e)
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
                    "You are a document consistency analyst for a government project review. "
                    "Compare the two provided documents and identify any contradictions, scope drift, or undocumented gaps. "
                    "Return a JSON object with key \"inconsistencies\" containing an array. "
                    "Each item must have: "
                    "id (string like INC-1), "
                    "type (contradiction|drift|gap), "
                    "document_a (filename), passage_a (exact quote from doc A), "
                    "document_b (filename), passage_b (exact quote from doc B), "
                    "explanation (2-3 sentences explaining the inconsistency and its project impact), "
                    "confidence (0.0-1.0), "
                    "recommendation (specific action to resolve). "
                    "Only report inconsistencies clearly supported by the text. "
                    "Return {\"inconsistencies\": []} if none found."
                )),
                Message(role="user", content=json.dumps({
                    "document_a": {"filename": doc_a["filename"], "type": doc_a["doc_type"], "text": doc_a["full_text"][:3000]},
                    "document_b": {"filename": doc_b["filename"], "type": doc_b["doc_type"], "text": doc_b["full_text"][:3000]},
                })),
            ],
            config_name="primary",
            response_format="json",
            max_tokens=16000,   # thinking models: ~12k thinking + ~3k JSON per pair
            temperature=0.2,
        )
        # LLM call errors propagate to caller
        response = await llm.complete(request)
        if not response.content.strip():
            continue
        # JSON parsing errors are non-fatal for individual pairs
        try:
            data = _extract_json(response.content)
            if data is None:
                logger.warning("Inconsistency detection: failed to extract JSON for pair (%s, %s)",
                               doc_a["filename"], doc_b["filename"])
                continue
            if isinstance(data, dict) and "inconsistencies" in data:
                data = data["inconsistencies"]
            for item in (data if isinstance(data, list) else []):
                inconsistencies.append(InconsistencyItem(
                    id=item.get("id") or str(uuid.uuid4())[:8],
                    type=item.get("type") or "contradiction",
                    document_a=item.get("document_a") or doc_a["filename"],
                    passage_a=item.get("passage_a") or "",
                    document_b=item.get("document_b") or doc_b["filename"],
                    passage_b=item.get("passage_b") or "",
                    explanation=item.get("explanation") or "",
                    confidence=float(item.get("confidence") or 0.6),
                    recommendation=item.get("recommendation") or "",
                ))
        except Exception as e:
            logger.error("Inconsistency detection: JSON parse error for pair (%s, %s): %s",
                         doc_a["filename"], doc_b["filename"], e)

    return inconsistencies


async def generate_report(
    project_id: uuid.UUID,
    risks: list[RiskItem],
    inconsistencies: list[InconsistencyItem],
    context: ProjectContext,
    llm: LLMGateway,
    model_name: str = "",
) -> RiskReport:
    """Combine all findings into final report with LLM-generated executive summary."""
    all_confidences = [r.confidence for r in risks] + [i.confidence for i in inconsistencies]
    overall_confidence = round(sum(all_confidences) / len(all_confidences), 2) if all_confidences else 0.0

    high_count = sum(1 for r in risks if r.probability_label == "High" or r.impact_label == "High")
    max_risk_score = max((r.risk_score for r in risks), default=0.0)
    if max_risk_score >= 0.8 or high_count >= 3:
        overall_risk_level = "critical"
    elif max_risk_score >= 0.6 or high_count >= 1:
        overall_risk_level = "high"
    elif max_risk_score >= 0.4:
        overall_risk_level = "medium"
    else:
        overall_risk_level = "low"

    executive_summary = await _generate_executive_summary(context, risks, inconsistencies, llm)

    return RiskReport(
        report_id=uuid.uuid4(),
        project_id=project_id,
        generated_at=datetime.now(timezone.utc),
        overall_risk_level=overall_risk_level,
        overall_confidence=overall_confidence,
        executive_summary=executive_summary,
        risks=risks,
        inconsistencies=inconsistencies,
        documents_analyzed=[d["filename"] for d in context.documents],
        methodology_notes=(
            "Risk identification: LLM analysis of project documents, emails, and tasks. "
            "Inconsistency detection: Pairwise LLM comparison across all document pairs. "
            "Output format aligned to government project gate review standard (Business Case risk table). "
            "Confidence scores are LLM self-reported estimates based on evidence strength."
        ),
        model_name=model_name,
    )


async def _generate_executive_summary(
    context: ProjectContext,
    risks: list[RiskItem],
    inconsistencies: list[InconsistencyItem],
    llm: LLMGateway,
) -> str:
    top_risks = sorted(risks, key=lambda r: r.risk_score, reverse=True)[:5]
    risk_lines = "\n".join(
        f"- {r.id} ({r.probability_label} probability / {r.impact_label} impact): {r.title or r.description[:80]}"
        for r in top_risks
    )
    inc_count = len(inconsistencies)

    prompt = f"""Write a concise executive summary (3-4 paragraphs) for a project risk analysis report.
The summary should be suitable for a steering committee or project sponsor.

Project: {context.project_name}
Documents analyzed: {len(context.documents)}
Total risks identified: {len(risks)}
Cross-document inconsistencies found: {inc_count}

Top risks:
{risk_lines}

The summary should:
1. State the purpose of the analysis and what was reviewed
2. Summarize the overall risk posture and most significant risks
3. Highlight any critical inconsistencies between documents
4. Conclude with a recommended course of action

Write in formal government project management language. Do not use bullet points in the summary."""

    try:
        request = LLMRequest(
            messages=[
                Message(role="system", content="You are a senior project manager writing a formal risk analysis report for a government steering committee."),
                Message(role="user", content=prompt),
            ],
            config_name="primary",
            max_tokens=8000,    # thinking models: ~5k thinking + ~2k summary text
            temperature=0.4,
        )
        response = await llm.complete(request)
        return response.content.strip()
    except Exception as e:
        logger.error("Executive summary generation failed: %s", e)
        top_risk_titles = "; ".join(r.title or r.description[:60] for r in top_risks)
        return (
            f"This risk analysis for project '{context.project_name}' reviewed {len(context.documents)} document(s) "
            f"and identified {len(risks)} risk(s) and {inc_count} cross-document inconsistency/inconsistencies. "
            f"Top risks: {top_risk_titles}. Review the detailed findings below."
        )


async def run_full_analysis(
    project_id: uuid.UUID,
    db: AsyncSession,
    llm: LLMGateway,
    web_search: bool = False,
) -> RiskReport:
    """Main entry point. Orchestrates all steps sequentially."""
    # Resolve the active LLM config to record model name in the report
    try:
        config = await llm._get_active_config("primary")
        model_name = f"{config.provider} / {config.model}"
    except Exception:
        model_name = ""

    context = await gather_project_data(project_id, db)
    risks = await risk_modelling(context, llm, web_search)
    inconsistencies = await inconsistency_detection(context, llm)
    return await generate_report(project_id, risks, inconsistencies, context, llm, model_name=model_name)


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
