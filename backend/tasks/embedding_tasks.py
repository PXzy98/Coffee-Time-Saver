import asyncio
import logging
import sys
import uuid
from pathlib import Path

_backend_dir = str(Path(__file__).resolve().parent.parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from tasks import celery_app

logger = logging.getLogger("coffee_time_saver")


@celery_app.task(name="tasks.embedding_tasks.regenerate_embeddings")
def regenerate_embeddings(document_id: str) -> None:
    """Re-generate embeddings for a document (e.g. after switching embedding model)."""
    import sys
    from pathlib import Path
    _bd = str(Path(__file__).resolve().parent.parent)
    if _bd not in sys.path:
        sys.path.insert(0, _bd)
    asyncio.run(_regenerate_async(uuid.UUID(document_id)))


async def _regenerate_async(document_id: uuid.UUID) -> None:
    import sys
    from pathlib import Path
    _bd = str(Path(__file__).resolve().parent.parent)
    if _bd not in sys.path:
        sys.path.insert(0, _bd)
    from core.database import engine, AsyncSessionLocal
    await engine.dispose()
    from modules.ingestion.embedder import Embedder

    async with AsyncSessionLocal() as db:
        await Embedder(db).regenerate_for_document(document_id)
