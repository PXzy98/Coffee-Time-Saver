"""
Risk analysis with layered summarization pipeline.

Pipeline:
  1. gather_project_data()       — full data, no truncation
  2. summarize_chunk() × N       — parallel chunk summarization (semaphore-bounded)
  3. build_document_summary()    — aggregate chunk summaries per document
  4. normalize_email/task        — pure code, no LLM
  5. build_evidence_pack()       — assemble final evidence pack
  6. risk_modelling()            — LLM risk identification from evidence pack
  7. inconsistency_detection()   — LLM pairwise comparison of document summaries
  8. compute_evidence_confidence — adjust confidence with evidence density
  9. generate_report()           — executive summary + final assembly
"""
import asyncio
import json
import logging
import re
import uuid
from datetime import date, datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from core.models import Document, DocumentChunk, Email, Task, Project
from modules.llm_gateway.service import LLMGateway
from modules.llm_gateway.schemas import LLMRequest, Message
from modules.tools.risk_analyzer.schemas import (
    ChunkSummary, DocumentSummary, EvidencePack,
    RiskItem, InconsistencyItem, RiskReport, ProjectContext,
)

logger = logging.getLogger("coffee_time_saver")


# ---------------------------------------------------------------------------
# 1. Data gathering (NO truncation)
# ---------------------------------------------------------------------------

async def gather_project_data(project_id: uuid.UUID, db: AsyncSession) -> ProjectContext:
    """Collect all documents (with chunks), emails, tasks for a project."""
    proj_result = await db.execute(select(Project).where(Project.id == project_id))
    project = proj_result.scalar_one_or_none()
    if project is None:
        raise ValueError(f"Project {project_id} not found")

    docs_result = await db.execute(
        select(Document)
        .options(selectinload(Document.chunks))
        .where(Document.project_id == project_id, Document.status == "completed")
    )
    documents = docs_result.scalars().all()

    emails_result = await db.execute(
        select(Email).where(Email.project_id == project_id)
    )
    emails = emails_result.scalars().all()

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
                "full_text": d.full_text or "",
                "doc_summary": d.doc_summary,
                "doc_summary_metadata": d.doc_summary_metadata,
                "chunks": [
                    {
                        "id": str(c.id),
                        "text": c.content_text,
                        "lang": c.content_lang,
                        "index": c.chunk_index,
                        "summary_text": c.summary_text,
                        "summary_metadata": c.summary_metadata,
                    }
                    for c in sorted(d.chunks, key=lambda c: c.chunk_index)
                ],
            }
            for d in documents
        ],
        emails=[
            {
                "id": str(e.id),
                "subject": e.subject or "",
                "from_address": e.from_address or "",
                "body_text": e.body_text or "",
                "received_at": str(e.received_at) if e.received_at else "",
            }
            for e in emails
        ],
        tasks=[
            {
                "id": str(t.id),
                "title": t.title or "",
                "description": t.description or "",
                "status": "completed" if t.is_completed else "pending",
                "priority": t.priority or 50,
                "due_date": str(t.due_date) if t.due_date else None,
            }
            for t in tasks
        ],
    )


# ---------------------------------------------------------------------------
# 2. Chunk summarization
# ---------------------------------------------------------------------------

_MIN_CHUNK_WORDS = 20


async def summarize_chunk(
    chunk: dict,
    doc_filename: str,
    doc_type: str,
    total_chunks: int,
    llm: LLMGateway,
) -> ChunkSummary:
    """Summarize a single chunk via LLM. Skips very short chunks."""
    text = chunk["text"] or ""
    chunk_id = chunk["id"]
    chunk_index = chunk["index"]

    # Skip trivially short chunks (headers, footers, whitespace)
    if len(text.split()) < _MIN_CHUNK_WORDS:
        return ChunkSummary(
            chunk_id=chunk_id,
            document_id="",
            chunk_index=chunk_index,
            summary=text.strip(),
            topic="minimal content",
        )

    request = LLMRequest(
        messages=[
            Message(role="system", content=(
                "You are a document analyst. Summarize this chunk from a project document.\n"
                "Return JSON: {\"summary\": \"...\", \"key_entities\": [...], \"risk_signals\": [...], \"topic\": \"...\"}\n"
                "- summary: 50-100 words capturing the key information\n"
                "- key_entities: named entities (people, organizations, systems, dates, dollar amounts)\n"
                "- risk_signals: any phrases indicating risk, uncertainty, delay, cost overrun, dependency, or concern\n"
                "- topic: 2-4 word topic label\n"
                "Only extract information directly supported by the text. Return valid JSON only."
            )),
            Message(role="user", content=(
                f"Document: {doc_filename} ({doc_type}), Chunk {chunk_index + 1}/{total_chunks}\n\n{text}"
            )),
        ],
        config_name="primary",
        response_format="json",
        max_tokens=2000,
        temperature=0.1,
    )

    response = await llm.complete(request)
    data = _extract_json(response.content)
    if not isinstance(data, dict):
        return ChunkSummary(
            chunk_id=chunk_id, document_id="", chunk_index=chunk_index,
            summary=text[:300], topic="parse_failed",
        )

    return ChunkSummary(
        chunk_id=chunk_id,
        document_id="",
        chunk_index=chunk_index,
        summary=(data.get("summary") or "")[:500],
        key_entities=data.get("key_entities") or [],
        risk_signals=data.get("risk_signals") or [],
        topic=(data.get("topic") or "")[:50],
    )


async def summarize_chunks_parallel(
    chunks: list[dict],
    doc_filename: str,
    doc_type: str,
    llm: LLMGateway,
    max_concurrent: int = 5,
) -> tuple[list[ChunkSummary], list[str]]:
    """Summarize all chunks with bounded concurrency. Returns (summaries, warnings)."""
    if not chunks:
        return [], []

    semaphore = asyncio.Semaphore(max_concurrent)
    warnings: list[str] = []
    total = len(chunks)

    async def _safe_summarize(chunk: dict) -> ChunkSummary:
        async with semaphore:
            try:
                return await summarize_chunk(chunk, doc_filename, doc_type, total, llm)
            except Exception as e:
                msg = f"Chunk summarization failed for {doc_filename} chunk {chunk['index']}: {e}"
                logger.warning(msg)
                warnings.append(msg)
                return ChunkSummary(
                    chunk_id=chunk["id"], document_id="", chunk_index=chunk["index"],
                    summary="(summarization failed)", topic="error",
                )

    results = await asyncio.gather(*[_safe_summarize(c) for c in chunks])
    return list(results), warnings


# ---------------------------------------------------------------------------
# 3. Document summary
# ---------------------------------------------------------------------------

async def build_document_summary(
    document_id: str,
    filename: str,
    doc_type: str,
    chunk_summaries: list[ChunkSummary],
    llm: LLMGateway,
) -> DocumentSummary:
    """Aggregate chunk summaries into a single document summary via LLM."""
    if not chunk_summaries:
        return DocumentSummary(
            document_id=document_id, filename=filename, doc_type=doc_type,
            summary="(no chunks to summarize)", chunk_count=0,
        )

    chunks_json = json.dumps([
        {"index": cs.chunk_index, "summary": cs.summary,
         "entities": cs.key_entities, "risks": cs.risk_signals, "topic": cs.topic}
        for cs in chunk_summaries
    ], indent=1)

    request = LLMRequest(
        messages=[
            Message(role="system", content=(
                "You are a project document analyst. Synthesize these chunk summaries into a single document summary.\n"
                "Return JSON: {\"summary\": \"...\", \"key_entities\": [...], \"risk_signals\": [...], \"commitments\": [...]}\n"
                "- summary: 200-400 words covering purpose, key decisions, and risk-relevant content\n"
                "- key_entities: consolidated list of named entities across all chunks\n"
                "- risk_signals: consolidated risk indicators (deduplicated)\n"
                "- commitments: specific promises, deadlines, deliverables, or obligations\n"
                "Consolidate repeated information. Separate explicit risks from implicit risks. Return valid JSON only."
            )),
            Message(role="user", content=(
                f"Document: {filename} ({doc_type}), {len(chunk_summaries)} chunks analyzed\n\n{chunks_json}"
            )),
        ],
        config_name="primary",
        response_format="json",
        max_tokens=4000,
        temperature=0.2,
    )

    response = await llm.complete(request)
    data = _extract_json(response.content)
    if not isinstance(data, dict):
        # Fallback: concatenate chunk summaries
        fallback = " ".join(cs.summary for cs in chunk_summaries)
        return DocumentSummary(
            document_id=document_id, filename=filename, doc_type=doc_type,
            summary=fallback[:2000], chunk_count=len(chunk_summaries),
        )

    return DocumentSummary(
        document_id=document_id,
        filename=filename,
        doc_type=doc_type,
        summary=(data.get("summary") or "")[:2000],
        key_entities=data.get("key_entities") or [],
        risk_signals=data.get("risk_signals") or [],
        commitments=data.get("commitments") or [],
        chunk_count=len(chunk_summaries),
    )


# ---------------------------------------------------------------------------
# 4. Evidence normalization (no LLM)
# ---------------------------------------------------------------------------

def normalize_email_evidence(emails: list[dict]) -> list[dict]:
    """Normalize all emails into structured evidence — no truncation."""
    return [
        {
            "id": em["id"],
            "subject": em.get("subject", ""),
            "from": em.get("from_address", ""),
            "date": em.get("received_at", ""),
            "body_text": em.get("body_text", ""),
            "word_count": len((em.get("body_text") or "").split()),
        }
        for em in emails
    ]


def normalize_task_evidence(tasks: list[dict]) -> list[dict]:
    """Normalize all tasks with computed overdue status."""
    today = date.today()
    result = []
    for t in tasks:
        due = t.get("due_date")
        overdue = False
        if due and t.get("status") != "completed":
            try:
                overdue = date.fromisoformat(str(due)) < today
            except (ValueError, TypeError):
                pass
        result.append({
            "id": t["id"],
            "title": t.get("title", ""),
            "description": (t.get("description") or "")[:500],
            "status": t.get("status", "pending"),
            "priority": t.get("priority", 50),
            "due_date": due,
            "overdue": overdue,
        })
    return result


# ---------------------------------------------------------------------------
# 5. Evidence pack assembly
# ---------------------------------------------------------------------------

def build_evidence_pack(
    project_name: str,
    document_summaries: list[DocumentSummary],
    email_evidence: list[dict],
    task_evidence: list[dict],
    total_chunks: int,
) -> EvidencePack:
    return EvidencePack(
        project_name=project_name,
        document_summaries=document_summaries,
        email_evidence=email_evidence,
        task_evidence=task_evidence,
        total_chunks_analyzed=total_chunks,
        total_documents=len(document_summaries),
        total_emails=len(email_evidence),
        total_tasks=len(task_evidence),
    )


def _build_evidence_prompt(pack: EvidencePack) -> str:
    """Serialize evidence pack into the user message for risk modelling."""
    parts = [f"Project: {pack.project_name}\n"]

    parts.append(f"=== Documents ({pack.total_documents}, {pack.total_chunks_analyzed} chunks analyzed) ===")
    for ds in pack.document_summaries:
        parts.append(f"\n[{ds.doc_type}] {ds.filename} ({ds.chunk_count} chunks):")
        parts.append(f"  Summary: {ds.summary}")
        if ds.commitments:
            parts.append(f"  Commitments: {'; '.join(ds.commitments)}")
        if ds.risk_signals:
            parts.append(f"  Risk signals: {'; '.join(ds.risk_signals)}")

    parts.append(f"\n=== Emails ({pack.total_emails}) ===")
    for em in pack.email_evidence:
        parts.append(f"  [{em['date']}] From: {em['from']} — Subject: {em['subject']}")
        body = em.get("body_text", "")
        if body:
            parts.append(f"    {body[:1000]}")

    parts.append(f"\n=== Tasks ({pack.total_tasks}) ===")
    for t in pack.task_evidence:
        overdue_tag = " [OVERDUE]" if t.get("overdue") else ""
        parts.append(f"  [{t['status']}] (P{t['priority']}) {t['title']}{overdue_tag}")
        if t.get("due_date"):
            parts.append(f"    Due: {t['due_date']}")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# 6. Risk modelling (from evidence pack)
# ---------------------------------------------------------------------------

_LABEL_TO_INT = {"low": 2, "medium": 3, "high": 4, "critical": 5}
_INT_TO_LABEL = {1: "Low", 2: "Low", 3: "Medium", 4: "High", 5: "High"}


def _parse_label(val: str) -> int:
    return _LABEL_TO_INT.get(str(val).lower().strip(), 3)


async def risk_modelling(
    evidence_pack: EvidencePack,
    llm: LLMGateway,
) -> list[RiskItem]:
    """LLM-based risk identification from layered evidence pack."""
    evidence_prompt = _build_evidence_prompt(evidence_pack)

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

Only include risks with clear evidence in the provided materials. Do not invent risks.
Prefer risks supported by multiple signals across documents, emails, or tasks.
When evidence is weak, lower confidence instead of fabricating certainty."""

    request = LLMRequest(
        messages=[
            Message(role="system", content=system_prompt),
            Message(role="user", content=evidence_prompt),
        ],
        config_name="primary",
        response_format="json",
        max_tokens=32000,
        temperature=0.3,
    )

    response = await llm.complete(request)
    logger.info("Risk modelling: LLM response length=%d", len(response.content))

    try:
        data = _extract_json(response.content)
        if data is None:
            logger.error("Risk modelling: failed to extract JSON")
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


# ---------------------------------------------------------------------------
# 7. Inconsistency detection (from document summaries)
# ---------------------------------------------------------------------------

async def inconsistency_detection(
    document_summaries: list[DocumentSummary],
    llm: LLMGateway,
) -> tuple[list[InconsistencyItem], list[str]]:
    """Compare document summaries pairwise for inconsistencies.
    Returns (inconsistencies, warnings)."""
    if len(document_summaries) < 2:
        return [], []

    doc_pairs = []
    for i, a in enumerate(document_summaries):
        for b in document_summaries[i + 1:]:
            doc_pairs.append((a, b))

    inconsistencies = []
    warnings = []
    semaphore = asyncio.Semaphore(5)

    async def _check_pair(a: DocumentSummary, b: DocumentSummary) -> tuple[list[InconsistencyItem], list[str]]:
        async with semaphore:
            request = LLMRequest(
                messages=[
                    Message(role="system", content=(
                        "You are a document consistency analyst for a government project gate review. "
                        "Compare the two provided document summaries and identify any contradictions, scope drift, or undocumented gaps. "
                        "Return a JSON object with key \"inconsistencies\" containing an array. "
                        "Each item must have: "
                        "id (string like INC-1), "
                        "type (contradiction|drift|gap), "
                        "document_a (filename), passage_a (supporting evidence from doc A summary), "
                        "document_b (filename), passage_b (supporting evidence from doc B summary), "
                        "explanation (2-3 sentences explaining the inconsistency and its project impact), "
                        "confidence (0.0-1.0), "
                        "recommendation (specific action to resolve). "
                        "Only report inconsistencies clearly supported by the summaries. "
                        "Return {\"inconsistencies\": []} if none found."
                    )),
                    Message(role="user", content=json.dumps({
                        "document_a": {
                            "filename": a.filename, "type": a.doc_type,
                            "summary": a.summary,
                            "commitments": a.commitments,
                            "risk_signals": a.risk_signals,
                        },
                        "document_b": {
                            "filename": b.filename, "type": b.doc_type,
                            "summary": b.summary,
                            "commitments": b.commitments,
                            "risk_signals": b.risk_signals,
                        },
                    })),
                ],
                config_name="primary",
                response_format="json",
                max_tokens=16000,
                temperature=0.2,
            )
            try:
                response = await llm.complete(request)
                if not response.content.strip():
                    return [], []
                data = _extract_json(response.content)
                if data is None:
                    msg = f"Inconsistency detection: failed to parse JSON for pair ({a.filename}, {b.filename})"
                    logger.warning(msg)
                    return [], [msg]
                if isinstance(data, dict) and "inconsistencies" in data:
                    data = data["inconsistencies"]
                pair_items = []
                for item in (data if isinstance(data, list) else []):
                    pair_items.append(InconsistencyItem(
                        id=item.get("id") or str(uuid.uuid4())[:8],
                        type=item.get("type") or "contradiction",
                        document_a=item.get("document_a") or a.filename,
                        passage_a=item.get("passage_a") or "",
                        document_b=item.get("document_b") or b.filename,
                        passage_b=item.get("passage_b") or "",
                        explanation=item.get("explanation") or "",
                        confidence=float(item.get("confidence") or 0.6),
                        recommendation=item.get("recommendation") or "",
                    ))
                return pair_items, []
            except Exception as e:
                msg = f"Inconsistency detection failed for pair ({a.filename}, {b.filename}): {e}"
                logger.error(msg)
                return [], [msg]

    pair_results = await asyncio.gather(*[_check_pair(a, b) for a, b in doc_pairs[:20]])
    for pair_items, pair_warnings in pair_results:
        inconsistencies.extend(pair_items)
        warnings.extend(pair_warnings)

    return inconsistencies, warnings


# ---------------------------------------------------------------------------
# 8. Evidence-based confidence adjustment
# ---------------------------------------------------------------------------

def compute_evidence_based_confidence(
    risk: RiskItem,
    chunk_summaries: list[ChunkSummary],
) -> float:
    """Adjust LLM self-reported confidence using evidence density.

    Checks how many chunk summaries mention keywords from the risk's
    source_quotes or title. More corroborating chunks → higher confidence.
    """
    if not chunk_summaries:
        return risk.confidence

    # Build keyword set from risk
    keywords = set()
    for quote in risk.source_quotes:
        for word in quote.lower().split():
            if len(word) > 4:
                keywords.add(word)
    for word in (risk.title or "").lower().split():
        if len(word) > 4:
            keywords.add(word)

    if not keywords:
        return risk.confidence

    # Count chunks with keyword overlap in risk_signals or summary
    supporting = 0
    for cs in chunk_summaries:
        chunk_text = (cs.summary + " " + " ".join(cs.risk_signals)).lower()
        if any(kw in chunk_text for kw in keywords):
            supporting += 1

    # Evidence density factor: 0.5 (no support) to 1.2 (strong support)
    ratio = supporting / len(chunk_summaries) if chunk_summaries else 0
    if supporting == 0:
        factor = 0.5
    elif ratio > 0.2:
        factor = 1.2
    elif ratio > 0.1:
        factor = 1.0
    else:
        factor = 0.8

    adjusted = min(1.0, risk.confidence * factor)
    risk.evidence_chunk_count = supporting
    return round(adjusted, 2)


# ---------------------------------------------------------------------------
# 9. Report generation
# ---------------------------------------------------------------------------

async def generate_report(
    project_id: uuid.UUID,
    risks: list[RiskItem],
    inconsistencies: list[InconsistencyItem],
    context: ProjectContext,
    llm: LLMGateway,
    model_name: str = "",
    warnings: list[str] | None = None,
    evidence_pack: EvidencePack | None = None,
) -> RiskReport:
    """Combine all findings into final report with LLM-generated executive summary."""
    warnings = warnings or []

    all_confidences = [r.adjusted_confidence or r.confidence for r in risks] + [i.confidence for i in inconsistencies]
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

    executive_summary = await _generate_executive_summary(context, risks, inconsistencies, llm, warnings)

    stats = {}
    if evidence_pack:
        stats = {
            "chunks_analyzed": evidence_pack.total_chunks_analyzed,
            "documents": evidence_pack.total_documents,
            "emails": evidence_pack.total_emails,
            "tasks": evidence_pack.total_tasks,
        }

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
            "Risk identification: Layered evidence pipeline — chunk-level summarization, "
            "document-level aggregation, then LLM risk analysis from structured evidence pack. "
            "Inconsistency detection: Pairwise LLM comparison of document summaries. "
            "Confidence scores: LLM self-reported estimates adjusted by evidence density across chunks."
        ),
        model_name=model_name,
        warnings=warnings,
        evidence_pack_stats=stats,
    )


async def _generate_executive_summary(
    context: ProjectContext,
    risks: list[RiskItem],
    inconsistencies: list[InconsistencyItem],
    llm: LLMGateway,
    warnings: list[str] | None = None,
) -> str:
    top_risks = sorted(risks, key=lambda r: r.risk_score, reverse=True)[:5]
    risk_lines = "\n".join(
        f"- {r.id} ({r.probability_label} probability / {r.impact_label} impact): {r.title or r.description[:80]}"
        for r in top_risks
    )
    inc_count = len(inconsistencies)
    warn_count = len(warnings) if warnings else 0

    prompt = f"""Write a concise executive summary (3-4 paragraphs) for a project risk analysis report.
The summary should be suitable for a steering committee or project sponsor.

Project: {context.project_name}
Documents analyzed: {len(context.documents)}
Total risks identified: {len(risks)}
Cross-document inconsistencies found: {inc_count}
{"Analysis warnings: " + str(warn_count) + " (some data could not be fully analyzed)" if warn_count else ""}

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
            max_tokens=8000,
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


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

async def run_full_analysis(
    project_id: uuid.UUID,
    db: AsyncSession,
    llm: LLMGateway,
    web_search: bool = False,
) -> RiskReport:
    """Main entry point — layered summarization pipeline."""
    if web_search:
        logger.warning("include_web_search=True is deprecated and ignored")

    # Resolve model name for report metadata
    try:
        config = await llm._get_active_config("primary")
        model_name = f"{config.provider} / {config.model}"
    except Exception:
        model_name = ""

    warnings: list[str] = []

    # 1. Gather full data
    context = await gather_project_data(project_id, db)

    # 2-3. Chunk summarization + document summarization
    #       Use pre-computed summaries from DB when available; fall back to LLM.
    all_chunk_summaries: list[ChunkSummary] = []
    document_summaries: list[DocumentSummary] = []

    for doc in context.documents:
        chunks = doc["chunks"]
        if not chunks:
            # Fallback: if document has full_text but no chunks, generate a
            # document summary directly from full_text via LLM so the document
            # still participates in risk modelling and inconsistency detection.
            full_text = (doc.get("full_text") or "").strip()
            if not full_text:
                warnings.append(f"Document '{doc['filename']}' has no chunks and no text — skipped")
                continue

            logger.info("Document '%s' has no chunks — falling back to full_text summary", doc["filename"])
            try:
                fake_chunk = ChunkSummary(
                    chunk_id="fulltext-0", document_id=doc["id"], chunk_index=0,
                    summary=full_text[:2000], topic="full document",
                )
                doc_summary = await build_document_summary(
                    doc["id"], doc["filename"], doc["doc_type"], [fake_chunk], llm,
                )
                document_summaries.append(doc_summary)
                all_chunk_summaries.append(fake_chunk)
            except Exception as e:
                msg = f"Fallback summary failed for '{doc['filename']}': {e}"
                logger.error(msg)
                warnings.append(msg)
            continue

        # --- Try loading pre-computed chunk summaries from DB ---
        precomputed_chunks = [c for c in chunks if c.get("summary_text")]
        if len(precomputed_chunks) == len(chunks):
            # All chunks have cached summaries — skip LLM calls
            chunk_sums = [
                ChunkSummary(
                    chunk_id=c["id"],
                    document_id=doc["id"],
                    chunk_index=c["index"],
                    summary=c["summary_text"],
                    key_entities=(c.get("summary_metadata") or {}).get("key_entities", []),
                    risk_signals=(c.get("summary_metadata") or {}).get("risk_signals", []),
                    topic=(c.get("summary_metadata") or {}).get("topic", ""),
                )
                for c in chunks
            ]
            logger.info("Using %d pre-computed chunk summaries for '%s'", len(chunk_sums), doc["filename"])
        else:
            # Compute from scratch via LLM
            for c in chunks:
                c["document_id"] = doc["id"]
            chunk_sums, chunk_warnings = await summarize_chunks_parallel(
                chunks, doc["filename"], doc["doc_type"], llm,
            )
            warnings.extend(chunk_warnings)
            for cs in chunk_sums:
                cs.document_id = doc["id"]

        all_chunk_summaries.extend(chunk_sums)

        # --- Try loading pre-computed document summary from DB ---
        if doc.get("doc_summary"):
            meta = doc.get("doc_summary_metadata") or {}
            doc_summary = DocumentSummary(
                document_id=doc["id"],
                filename=doc["filename"],
                doc_type=doc["doc_type"],
                summary=doc["doc_summary"],
                key_entities=meta.get("key_entities", []),
                risk_signals=meta.get("risk_signals", []),
                commitments=meta.get("commitments", []),
                chunk_count=meta.get("chunk_count", len(chunks)),
            )
            logger.info("Using pre-computed document summary for '%s'", doc["filename"])
            document_summaries.append(doc_summary)
        else:
            try:
                doc_summary = await build_document_summary(
                    doc["id"], doc["filename"], doc["doc_type"], chunk_sums, llm,
                )
                document_summaries.append(doc_summary)
            except Exception as e:
                msg = f"Document summary failed for '{doc['filename']}': {e}"
                logger.error(msg)
                warnings.append(msg)

    # 4. Normalize evidence
    email_evidence = normalize_email_evidence(context.emails)
    task_evidence = normalize_task_evidence(context.tasks)

    # 5. Build evidence pack
    evidence_pack = build_evidence_pack(
        context.project_name, document_summaries, email_evidence, task_evidence,
        total_chunks=len(all_chunk_summaries),
    )

    # 6. Risk modelling
    try:
        risks = await risk_modelling(evidence_pack, llm)
    except Exception as e:
        msg = f"Risk modelling failed: {e}"
        logger.error(msg)
        warnings.append(msg)
        risks = []

    # 7. Adjust confidence
    for risk in risks:
        risk.adjusted_confidence = compute_evidence_based_confidence(risk, all_chunk_summaries)

    # 8. Inconsistency detection
    try:
        inconsistencies, inc_warnings = await inconsistency_detection(document_summaries, llm)
        warnings.extend(inc_warnings)
    except Exception as e:
        msg = f"Inconsistency detection failed: {e}"
        logger.error(msg)
        warnings.append(msg)
        inconsistencies = []

    # 9. Generate report
    return await generate_report(
        project_id, risks, inconsistencies, context, llm,
        model_name=model_name, warnings=warnings, evidence_pack=evidence_pack,
    )


# ---------------------------------------------------------------------------
# JSON extraction helper
# ---------------------------------------------------------------------------

def _extract_json(raw: str) -> dict | list | None:
    """Robustly extract JSON from LLM output that may contain thinking/reasoning text."""
    raw = raw.strip()
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)```", raw, re.DOTALL)
    if fence_match:
        raw = fence_match.group(1).strip()
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
