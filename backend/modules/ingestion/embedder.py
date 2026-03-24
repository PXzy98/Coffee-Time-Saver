import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.models import DocumentChunk

logger = logging.getLogger("coffee_time_saver")


class Embedder:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def embed_chunks(self, chunks: list[DocumentChunk], llm_gateway) -> None:
        """Generate embeddings for a list of DocumentChunk objects and persist them."""
        texts = [c.content_text for c in chunks]
        if not texts:
            return
        try:
            vectors = await llm_gateway.embed(texts, config_name="embedding")
            for chunk, vector in zip(chunks, vectors):
                chunk.embedding = vector
        except Exception as e:
            logger.warning("Embedding failed: %s — chunks stored without vectors", e)

    async def regenerate_for_document(self, document_id: uuid.UUID) -> None:
        from core.database import AsyncSessionLocal
        from modules.llm_gateway.service import LLMGateway

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(DocumentChunk).where(DocumentChunk.document_id == document_id)
            )
            chunks = result.scalars().all()
            llm = LLMGateway(db)
            await self.embed_chunks(chunks, llm)
            await db.commit()
