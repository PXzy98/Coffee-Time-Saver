import asyncio
import logging
import sys
import uuid
from pathlib import Path

# Ensure backend directory is on sys.path regardless of working directory
_backend_dir = str(Path(__file__).resolve().parent.parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from tasks import celery_app

logger = logging.getLogger("coffee_time_saver")


@celery_app.task(name="tasks.file_tasks.process_file", bind=True, max_retries=3)
def process_file(self, document_id: str) -> None:
    """Parse → chunk → detect language → structure → embed → notify."""
    import sys
    from pathlib import Path
    _bd = str(Path(__file__).resolve().parent.parent)
    if _bd not in sys.path:
        sys.path.insert(0, _bd)
    asyncio.run(_process_file_async(uuid.UUID(document_id)))


async def _process_file_async(document_id: uuid.UUID) -> None:
    import sys
    from pathlib import Path
    _bd = str(Path(__file__).resolve().parent.parent)
    if _bd not in sys.path:
        sys.path.insert(0, _bd)
    from config import settings
    from core.database import engine, AsyncSessionLocal
    await engine.dispose()  # Reset connection pool for this event loop
    from core.models import Document
    from modules.file_processing.service import FileProcessingService
    from modules.file_processing.document_intelligence import (
        extract_tasks,
        suggest_project,
        associate_tasks_to_projects,
    )
    from modules.llm_gateway.service import LLMGateway
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        await FileProcessingService(db).run_pipeline(document_id)

        # Post-processing intelligence (best-effort — never blocks the pipeline)
        try:
            result = await db.execute(select(Document).where(Document.id == document_id))
            doc = result.scalar_one_or_none()
            if doc and doc.status == "completed" and doc.full_text:
                llm = LLMGateway(db)

                created_tasks = await extract_tasks(doc, db, llm)
                await suggest_project(doc, db, llm)

                # LLM-based task-to-project association
                if settings.TASK_PROJECT_ASSOCIATION == "llm" and created_tasks:
                    await associate_tasks_to_projects(created_tasks, db, llm)

        except Exception as e:
            logger.warning("Post-processing intelligence failed for %s: %s", document_id, e)
