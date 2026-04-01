"""
Post-processing intelligence layer — runs after a document is fully parsed and ingested.

Two capabilities:
  1. extract_tasks()    — LLM identifies action items / commitments → creates Task rows
  2. suggest_project()  — LLM matches document to an existing project (or proposes a new one)
                          → pushes a WebSocket suggestion event (never auto-creates)
"""
import json
import logging
import uuid
from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.models import Document, Task, Project
from core.websocket import manager
from modules.llm_gateway.service import LLMGateway
from modules.llm_gateway.schemas import LLMRequest, Message

logger = logging.getLogger("coffee_time_saver")

# Cap how much document text we send to the LLM for each call
_MAX_TEXT = 6000


# ---------------------------------------------------------------------------
# 1. Task extraction
# ---------------------------------------------------------------------------

async def extract_tasks(document: Document, db: AsyncSession, llm: LLMGateway) -> list[Task]:
    """Extract action items and commitments from a document and create Task rows."""
    if not document.full_text or not document.uploaded_by:
        return []

    text = document.full_text[:_MAX_TEXT]

    request = LLMRequest(
        messages=[
            Message(role="system", content="""You are a project management assistant.
Read the provided document and extract every actionable item: tasks, commitments, decisions requiring follow-up, and deadlines.

Return a JSON object with key "tasks" containing an array. Each task must have:
- "title": clear, concise action title (max 120 characters, starts with a verb)
- "description": 1-2 sentences of context from the document
- "priority": integer 1-100 (100 = most urgent; base on urgency language and deadlines)
- "due_date": ISO date string "YYYY-MM-DD" if a deadline is mentioned, otherwise null
- "source_quote": the exact sentence or phrase from the document that triggered this task

Only extract genuine action items. Do not invent tasks not supported by the text.
Return {"tasks": []} if no clear action items exist."""),
            Message(role="user", content=f"Document: {document.filename}\n\n{text}"),
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
        for item in items[:10]:  # cap at 10 tasks per document
            title = (item.get("title") or "").strip()
            if not title:
                continue

            due_date = _parse_date(item.get("due_date"))
            desc = item.get("description", "")
            quote = item.get("source_quote", "")
            full_desc = f"{desc}\n\nSource: \"{quote}\"" if quote else desc

            task = Task(
                id=uuid.uuid4(),
                user_id=document.uploaded_by,
                project_id=document.project_id,
                title=title[:500],
                description=full_desc[:2000],
                priority=min(100, max(1, int(item.get("priority", 50)))),
                due_date=due_date,
                source="document",
                sort_score=float(item.get("priority", 50)),
            )
            db.add(task)
            created.append(task)

        if created:
            await db.commit()
            logger.info("Extracted %d task(s) from document %s", len(created), document.filename)

        return created

    except Exception as e:
        logger.error("Task extraction failed for %s: %s", document.filename, e)
        return []


# ---------------------------------------------------------------------------
# 2. Project suggestion
# ---------------------------------------------------------------------------

async def suggest_project(document: Document, db: AsyncSession, llm: LLMGateway) -> None:
    """
    Compare document content against existing projects and push a suggestion
    event via WebSocket. Never creates a project automatically.
    """
    if not document.full_text or not document.uploaded_by:
        return

    # Fetch existing projects (name + description only — keep prompt small)
    result = await db.execute(select(Project).where(Project.status != "archived"))
    projects = result.scalars().all()

    project_list = "\n".join(
        f"- id={p.id}  name=\"{p.name}\"  desc=\"{(p.description or '')[:120]}\""
        for p in projects
    )

    text_preview = document.full_text[:3000]

    request = LLMRequest(
        messages=[
            Message(role="system", content="""You are a project management assistant.
Given a document and a list of existing projects, determine whether the document belongs to one of them.

Return a JSON object with:
- "match_type": "existing" | "new" | "none"
  - "existing" → document clearly relates to a known project
  - "new"      → document represents a new project not in the list
  - "none"     → document is a general/reference file, no project association
- "project_id": the UUID of the matching project (only when match_type is "existing"), otherwise null
- "project_name": the matched project name, or a suggested name for a new project
- "confidence": float 0.0-1.0
- "reason": one sentence explaining why

Only return match_type "existing" when you are confident (confidence >= 0.7)."""),
            Message(role="user", content=(
                f"Document filename: {document.filename}\n"
                f"Document preview:\n{text_preview}\n\n"
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

        # Build suggestion payload
        payload = {
            "document_id": str(document.id),
            "document_name": document.filename,
            "match_type": match_type,          # "existing" or "new"
            "project_id": project_id,           # UUID string or null
            "project_name": project_name,
            "confidence": confidence,
            "reason": reason,
        }

        await manager.publish(
            document.uploaded_by,
            {"type": "project.suggestion", "payload": payload},
        )

        logger.info(
            "Project suggestion for %s: match_type=%s project=%s confidence=%.2f",
            document.filename, match_type, project_name, confidence,
        )

    except Exception as e:
        logger.error("Project suggestion failed for %s: %s", document.filename, e)


# ---------------------------------------------------------------------------
# 3. LLM-based task-to-project association
# ---------------------------------------------------------------------------

async def associate_tasks_to_projects(
    tasks: list[Task], db: AsyncSession, llm: LLMGateway
) -> None:
    """
    Use LLM to match tasks (that have no project_id) to existing projects.
    Updates task.project_id in place and commits.
    Shared by both file and email pipelines.
    """
    unassigned = [t for t in tasks if t.project_id is None]
    if not unassigned:
        return

    result = await db.execute(select(Project).where(Project.status != "archived"))
    projects = result.scalars().all()
    if not projects:
        return

    project_list = "\n".join(
        f"- id={p.id}  name=\"{p.name}\"  desc=\"{(p.description or '')[:120]}\""
        for p in projects
    )

    task_list = "\n".join(
        f"- task_id={t.id}  title=\"{t.title}\"  desc=\"{(t.description or '')[:150]}\""
        for t in unassigned
    )

    request = LLMRequest(
        messages=[
            Message(role="system", content="""You are a project management assistant.
Given a list of tasks and a list of existing projects, determine which project each task belongs to.

Return a JSON object with key "assignments" containing an array. Each entry must have:
- "task_id": the UUID of the task
- "project_id": the UUID of the matching project, or null if no good match
- "confidence": float 0.0-1.0

Only assign a task to a project when confidence >= 0.7. Leave project_id as null otherwise."""),
            Message(role="user", content=(
                f"Tasks:\n{task_list}\n\n"
                f"Existing projects:\n{project_list}"
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
        assignments = data.get("assignments", [])
        if not isinstance(assignments, list):
            return

        # Build lookup for quick access
        task_map = {str(t.id): t for t in unassigned}
        project_ids = {str(p.id) for p in projects}
        updated = 0

        for entry in assignments:
            tid = entry.get("task_id")
            pid = entry.get("project_id")
            conf = float(entry.get("confidence", 0.0))

            if not tid or not pid or conf < 0.7:
                continue
            if tid not in task_map or pid not in project_ids:
                continue

            task_map[tid].project_id = uuid.UUID(pid)
            updated += 1

        if updated:
            await db.commit()
            logger.info("LLM associated %d task(s) to projects", updated)

    except Exception as e:
        logger.error("Task-to-project association failed: %s", e)


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


def _parse_date(val) -> date | None:
    if not val or val == "null":
        return None
    try:
        return date.fromisoformat(str(val))
    except Exception:
        return None
