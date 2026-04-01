import hashlib
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

        # 4. Pre-compute summaries (best-effort, requires LLM)
        if llm:
            try:
                await self._summarize_and_persist(doc, chunk_objects, llm)
            except Exception as e:
                logger.warning("Summarization failed for %s: %s", document_id, e)

        await self.db.commit()
        logger.info("Ingestion complete for document %s", document_id)

    async def _summarize_and_persist(
        self,
        doc: Document,
        chunk_objects: list[DocumentChunk],
        llm,
    ) -> None:
        """Compute chunk + document summaries and persist to DB."""
        from modules.tools.risk_analyzer.analyzer import (
            summarize_chunks_parallel,
            build_document_summary,
        )

        # Resolve model name
        try:
            config = await llm._get_active_config("primary")
            model_name = f"{config.provider}/{config.model}"
        except Exception:
            model_name = "unknown"

        # Build chunk dicts for the summarizer
        chunks_for_summary = [
            {"id": str(c.id), "text": c.content_text, "index": c.chunk_index}
            for c in chunk_objects
        ]

        # Chunk summaries (parallel, bounded concurrency)
        chunk_summaries, warnings = await summarize_chunks_parallel(
            chunks_for_summary, doc.filename, doc.doc_type, llm,
        )
        if warnings:
            logger.warning("Chunk summarization warnings for %s: %s", doc.id, warnings)

        # Persist chunk summaries
        for cs, chunk_obj in zip(chunk_summaries, chunk_objects):
            chunk_obj.summary_text = cs.summary
            chunk_obj.summary_metadata = {
                "key_entities": cs.key_entities,
                "risk_signals": cs.risk_signals,
                "topic": cs.topic,
            }
            chunk_obj.summary_model = model_name
            chunk_obj.content_hash = hashlib.sha256(
                chunk_obj.content_text.encode()
            ).hexdigest()

        # Document summary
        doc_summary = await build_document_summary(
            str(doc.id), doc.filename, doc.doc_type, chunk_summaries, llm,
        )

        doc.doc_summary = doc_summary.summary
        doc.doc_summary_metadata = {
            "key_entities": doc_summary.key_entities,
            "risk_signals": doc_summary.risk_signals,
            "commitments": doc_summary.commitments,
            "chunk_count": doc_summary.chunk_count,
        }
        doc.doc_summary_model = model_name
        doc.doc_summary_hash = hashlib.sha256(
            "".join(c.content_hash or "" for c in chunk_objects).encode()
        ).hexdigest()

        logger.info(
            "Summaries persisted for document %s: %d chunk summaries + 1 doc summary",
            doc.id, len(chunk_summaries),
        )
