import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config import settings
from core.models import Document, DocumentChunk
from core.exceptions import NotFoundError
from modules.ingestion.chunker import chunk_text
from modules.ingestion.language_detect import detect_language
from modules.ingestion.structurer import get_structurer
from modules.ingestion.embedder import Embedder

logger = logging.getLogger("coffee_time_saver")


class IngestionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def process_document(self, document_id: uuid.UUID) -> None:
        result = await self.db.execute(select(Document).where(Document.id == document_id))
        doc = result.scalar_one_or_none()
        if doc is None:
            raise NotFoundError(f"Document {document_id} not found")

        if not doc.full_text:
            logger.warning("Document %s has no full_text — skipping ingestion", document_id)
            return

        # 1. Chunk
        chunks_text = chunk_text(doc.full_text)
        logger.info("Document %s → %d chunks", document_id, len(chunks_text))

        # 2. Detect language + Structure
        try:
            from modules.llm_gateway.service import LLMGateway
            llm = LLMGateway(self.db)
        except Exception:
            llm = None

        structurer = get_structurer(settings.STRUCTURER_STRATEGY, llm)
        embedder = Embedder(self.db)

        chunk_objects = []
        for idx, chunk_text_content in enumerate(chunks_text):
            lang = detect_language(chunk_text_content)
            structured = await structurer.structure(chunk_text_content)
            chunk = DocumentChunk(
                document_id=document_id,
                chunk_index=idx,
                content_text=chunk_text_content,
                content_lang=lang,
                structured_data=structured,
            )
            self.db.add(chunk)
            chunk_objects.append(chunk)

        await self.db.flush()  # get IDs assigned

        # 3. Embed
        if llm:
            await embedder.embed_chunks(chunk_objects, llm)

        await self.db.commit()
        logger.info("Ingestion complete for document %s", document_id)
