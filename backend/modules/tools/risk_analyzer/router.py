import uuid
from typing import Optional

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.auth.dependencies import get_current_user
from core.models import User
from core.logging import audit_log
from modules.tools.risk_analyzer.schemas import (
    RiskAnalyzerRunRequest, RiskReport, RunStatusResponse,
)

router = APIRouter(prefix="/api/tools/risk-analyzer", tags=["risk-analyzer"])

# Redis-backed report store — persists across restarts and works with multiple workers
import json as _json

async def _set_report(report_id: str, data: dict) -> None:
    from core.websocket import manager
    import redis.asyncio as aioredis
    from config import settings
    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        # Serialize RiskReport to JSON if present
        serializable = {**data}
        if serializable.get("report"):
            serializable["report"] = serializable["report"].model_dump(mode="json")
        await r.set(f"risk_report:{report_id}", _json.dumps(serializable), ex=86400)  # 24h TTL
    finally:
        await r.aclose()


async def _get_report(report_id: str) -> dict | None:
    import redis.asyncio as aioredis
    from config import settings
    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        raw = await r.get(f"risk_report:{report_id}")
        if raw is None:
            return None
        data = _json.loads(raw)
        # Deserialize RiskReport back from dict
        if data.get("report"):
            from modules.tools.risk_analyzer.schemas import RiskReport
            data["report"] = RiskReport(**data["report"])
        return data
    finally:
        await r.aclose()


@router.post("/run", response_model=RunStatusResponse, status_code=202)
async def run_risk_analysis(
    body: RiskAnalyzerRunRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    report_id = uuid.uuid4()
    await _set_report(str(report_id), {"status": "running", "report": None, "error": None})

    background_tasks.add_task(
        _run_analysis_bg,
        str(report_id),
        body.project_id,
        body.include_web_search,
        current_user.id,
    )

    await audit_log(db, action="module.risk_analyzer.invoke", entity_type="project",
                    entity_id=str(body.project_id), user_id=current_user.id,
                    details={"include_web_search": body.include_web_search})

    return RunStatusResponse(report_id=report_id, status="running")


@router.get("/status/{report_id}", response_model=RunStatusResponse)
async def get_status(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
):
    entry = await _get_report(str(report_id))
    if entry is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return RunStatusResponse(
        report_id=report_id,
        status=entry["status"],
        message=entry.get("error"),
    )


@router.get("/report/{report_id}", response_model=RiskReport)
async def get_report(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
):
    entry = await _get_report(str(report_id))
    if entry is None or entry["status"] != "completed":
        raise HTTPException(status_code=404, detail="Report not ready")
    return entry["report"]


@router.get("/report/{report_id}/download")
async def download_report(
    report_id: uuid.UUID,
    format: str = "pdf",
    current_user: User = Depends(get_current_user),
):
    entry = await _get_report(str(report_id))
    if entry is None or entry["status"] != "completed":
        raise HTTPException(status_code=404, detail="Report not ready")

    report: RiskReport = entry["report"]
    from modules.tools.risk_analyzer.report_generator import generate_pdf, generate_docx

    if format == "docx":
        content = generate_docx(report)
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        filename = f"risk_report_{report_id}.docx"
    else:
        content = generate_pdf(report)
        media_type = "application/pdf"
        filename = f"risk_report_{report_id}.pdf"

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


async def _run_analysis_bg(
    report_id: str,
    project_id: uuid.UUID,
    include_web_search: bool,
    user_id: uuid.UUID,
) -> None:
    import logging
    from core.database import AsyncSessionLocal
    from modules.llm_gateway.service import LLMGateway
    from modules.tools.risk_analyzer.analyzer import run_full_analysis

    logger = logging.getLogger("coffee_time_saver")

    if include_web_search:
        logger.warning(
            "include_web_search=True was requested for report %s but web search "
            "is not implemented — the flag is ignored.",
            report_id,
        )

    try:
        async with AsyncSessionLocal() as db:
            llm = LLMGateway(db)
            report = await run_full_analysis(project_id, db, llm)
        await _set_report(report_id, {"status": "completed", "report": report, "error": None})

        from core.websocket import manager
        await manager.publish(user_id, {
            "type": "tool.risk_analyzer.completed",
            "payload": {"report_id": report_id},
        })
    except Exception as e:
        await _set_report(report_id, {"status": "failed", "report": None, "error": str(e)})
