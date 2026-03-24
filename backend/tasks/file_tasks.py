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
    from modules.ingestion.service import IngestionService
    from modules.file_processing.service import FileProcessingService

    async with AsyncSessionLocal() as db:
        await FileProcessingService(db).run_pipeline(document_id)
