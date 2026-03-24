import asyncio
import logging
import uuid

from tasks import celery_app

logger = logging.getLogger("coffee_time_saver")


@celery_app.task(name="tasks.embedding_tasks.regenerate_embeddings")
def regenerate_embeddings(document_id: str) -> None:
    """Re-generate embeddings for a document (e.g. after switching embedding model)."""
    asyncio.run(_regenerate_async(uuid.UUID(document_id)))


async def _regenerate_async(document_id: uuid.UUID) -> None:
    from core.database import AsyncSessionLocal
    from modules.ingestion.embedder import Embedder

    async with AsyncSessionLocal() as db:
        await Embedder(db).regenerate_for_document(document_id)
