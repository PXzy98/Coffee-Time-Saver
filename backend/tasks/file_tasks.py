import asyncio
import logging
import uuid

from tasks import celery_app

logger = logging.getLogger("coffee_time_saver")


@celery_app.task(name="tasks.file_tasks.process_file", bind=True, max_retries=3)
def process_file(self, document_id: str) -> None:
    """Parse → chunk → detect language → structure → embed → notify."""
    asyncio.run(_process_file_async(uuid.UUID(document_id)))


async def _process_file_async(document_id: uuid.UUID) -> None:
    from core.database import AsyncSessionLocal
    from core.models import Document
    from modules.file_processing.service import FileProcessingService
    from modules.file_processing.document_intelligence import extract_tasks, suggest_project
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
                await extract_tasks(doc, db, llm)
                await suggest_project(doc, db, llm)
        except Exception as e:
            logger.warning("Post-processing intelligence failed for %s: %s", document_id, e)
