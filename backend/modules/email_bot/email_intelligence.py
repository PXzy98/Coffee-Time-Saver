"""
Post-processing intelligence for emails — mirrors document_intelligence.py.

Two capabilities:
  1. extract_tasks_from_email()  — LLM extracts action items from email body → creates Task rows
  2. suggest_project_for_email() — LLM matches email to existing project or suggests new one
                                   → pushes WebSocket suggestion event (never auto-creates)
"""
import json
import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.models import Email, Task, Project
from core.websocket import manager
from modules.llm_gateway.service import LLMGateway
from modules.llm_gateway.schemas import LLMRequest, Message

logger = logging.getLogger("coffee_time_saver")

_MAX_TEXT = 6000


# ---------------------------------------------------------------------------
# 1. LLM-based task extraction from email
# ---------------------------------------------------------------------------

async def extract_tasks_from_email(
    email_row: Email, user_id, db: AsyncSession, llm: LLMGateway
) -> list[Task]:
    """Extract action items from an email body using LLM and create Task rows."""
    body = (email_row.body_text or "").strip()
    if not body:
        return []

    text = body[:_MAX_TEXT]
    subject = email_row.subject or "(no subject)"

    request = LLMRequest(
        messages=[
            Message(role="system", content="""You are a project management assistant.
Read the provided email and extract every actionable item: tasks, commitments, requests, decisions requiring follow-up, and deadlines.

Return a JSON object with key "tasks" containing an array. Each task must have:
- "title": clear, concise action title (max 120 characters, starts with a verb)
- "description": 1-2 sentences of context from the email
- "priority": integer 1-100 (100 = most urgent; base on urgency language and deadlines)
- "due_date": ISO date string "YYYY-MM-DD" if a deadline is mentioned, otherwise null
- "source_quote": the exact sentence or phrase from the email that triggered this task

Only extract genuine action items. Do not invent tasks not supported by the text.
Return {"tasks": []} if no clear action items exist."""),
            Message(role="user", content=f"Email subject: {subject}\nFrom: {email_row.from_address or 'unknown'}\n\n{text}"),
        ],
        config_name="primary",
        response_format="json",
        max_tokens=6000,
        temperature=0.2,
    )

    try:
        response = await llm.complete(request)
        raw = _strip_fences(response.content)
        data = json.loads(raw)
        items = data.get("tasks", data) if isinstance(data, dict) else data
        if not isinstance(items, list):
            return []

        created: list[Task] = []
        for item in items[:10]:
            title = (item.get("title") or "").strip()
            if not title:
                continue

            due_date = _parse_date(item.get("due_date"))
            desc = item.get("description", "")
            quote = item.get("source_quote", "")
            full_desc = f"{desc}\n\nSource: \"{quote}\"" if quote else desc
            full_desc = f"From email: {subject}\n{full_desc}"

            task = Task(
                id=uuid.uuid4(),
                user_id=user_id,
                project_id=email_row.project_id,
                title=title[:500],
                description=full_desc[:2000],
                priority=min(100, max(1, int(item.get("priority", 50)))),
                due_date=due_date,
                source="email",
                sort_score=float(item.get("priority", 50)),
            )
            db.add(task)
            created.append(task)

        if created:
            await db.commit()
            logger.info("LLM extracted %d task(s) from email '%s'", len(created), subject)

        return created

    except Exception as e:
        logger.error("LLM task extraction failed for email '%s': %s", subject, e)
        return []


# ---------------------------------------------------------------------------
# 2. Project suggestion for email
# ---------------------------------------------------------------------------

async def suggest_project_for_email(
    email_row: Email, user_id, db: AsyncSession, llm: LLMGateway
) -> None:
    """
    Compare email content against existing projects and push a suggestion
    event via WebSocket. Never creates a project automatically.
    """
    body = (email_row.body_text or "").strip()
    if not body:
        return

    result = await db.execute(select(Project).where(Project.status != "archived"))
    projects = result.scalars().all()

    project_list = "\n".join(
        f"- id={p.id}  name=\"{p.name}\"  desc=\"{(p.description or '')[:120]}\""
        for p in projects
    )

    text_preview = body[:3000]
    subject = email_row.subject or "(no subject)"

    request = LLMRequest(
        messages=[
            Message(role="system", content="""You are a project management assistant.
Given an email and a list of existing projects, determine whether the email belongs to one of them.

Return a JSON object with:
- "match_type": "existing" | "new" | "none"
  - "existing" → email clearly relates to a known project
  - "new"      → email represents work for a new project not in the list
  - "none"     → email is general/personal, no project association
- "project_id": the UUID of the matching project (only when match_type is "existing"), otherwise null
- "project_name": the matched project name, or a suggested name for a new project
- "confidence": float 0.0-1.0
- "reason": one sentence explaining why

Only return match_type "existing" when you are confident (confidence >= 0.7)."""),
            Message(role="user", content=(
                f"Email subject: {subject}\n"
                f"From: {email_row.from_address or 'unknown'}\n\n"
                f"Email body:\n{text_preview}\n\n"
                f"Existing projects:\n{project_list or '(none yet)'}"
            )),
        ],
        config_name="primary",
        response_format="json",
        max_tokens=4000,
        temperature=0.1,
    )

    try:
        response = await llm.complete(request)
        raw = _strip_fences(response.content)
        data = json.loads(raw)

        match_type = data.get("match_type", "none")
        confidence = float(data.get("confidence", 0.0))
        project_name = data.get("project_name", "")
        project_id = data.get("project_id")
        reason = data.get("reason", "")

        if match_type == "none" or confidence < 0.5:
            return

        payload = {
            "source": "email",
            "email_id": str(email_row.id),
            "email_subject": subject,
            "match_type": match_type,
            "project_id": project_id,
            "project_name": project_name,
            "confidence": confidence,
            "reason": reason,
        }

        await manager.publish(
            user_id,
            {"type": "project.suggestion", "payload": payload},
        )

        logger.info(
            "Project suggestion for email '%s': match_type=%s project=%s confidence=%.2f",
            subject, match_type, project_name, confidence,
        )

    except Exception as e:
        logger.error("Project suggestion failed for email '%s': %s", subject, e)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else text
        if text.startswith("json"):
            text = text[4:]
    return text.strip()


def _parse_date(val) -> None:
    if not val or val == "null":
        return None
    try:
        from datetime import date
        return date.fromisoformat(str(val))
    except Exception:
        return None
