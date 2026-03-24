import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config import settings
from core.models import Document
from core.exceptions import NotFoundError
from modules.file_processing.parsers.base import FileParser
from modules.file_processing.parsers.pdf_parser import PyMuPDFParser
from modules.file_processing.parsers.docx_parser import DocxParser
from modules.file_processing.parsers.xlsx_parser import XlsxParser
from modules.file_processing.parsers.text_parser import TextParser

logger = logging.getLogger("coffee_time_saver")

_MIME_PARSERS: dict[str, FileParser] = {
    "application/pdf": PyMuPDFParser(),
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DocxParser(),
    "application/msword": DocxParser(),
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": XlsxParser(),
    "application/vnd.ms-excel": XlsxParser(),
    "text/csv": XlsxParser(),
    "text/plain": TextParser(),
    "text/markdown": TextParser(),
}


def _get_parser(mime_type: str, filename: str) -> FileParser:
    parser = _MIME_PARSERS.get(mime_type)
    if parser:
        return parser
    # Fallback by extension
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    ext_map = {"pdf": PyMuPDFParser(), "docx": DocxParser(), "doc": DocxParser(),
               "xlsx": XlsxParser(), "xls": XlsxParser(), "csv": XlsxParser(),
               "txt": TextParser(), "md": TextParser()}
    return ext_map.get(ext, TextParser())


class FileProcessingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def run_pipeline(self, document_id: uuid.UUID) -> None:
        result = await self.db.execute(select(Document).where(Document.id == document_id))
        doc = result.scalar_one_or_none()
        if doc is None:
            raise NotFoundError(f"Document {document_id} not found")

        try:
            doc.status = "processing"
            await self.db.commit()

            # The raw bytes were stored temporarily; retrieve and parse
            # In practice, file bytes come from the upload handler below
            # This method is called after bytes are already stored in full_text placeholder
            # The actual parsing is done in the upload router before dispatching

            from modules.ingestion.service import IngestionService
            await IngestionService(self.db).process_document(document_id)

            doc.status = "completed"
        except Exception as e:
            logger.error("File processing failed for %s: %s", document_id, e)
            doc.status = "failed"
        finally:
            await self.db.commit()
            # Push WebSocket notification
            from core.websocket import manager
            import asyncio
            asyncio.create_task(manager.publish(
                doc.uploaded_by,
                {"type": "file.status_changed", "payload": {"document_id": str(document_id), "status": doc.status}}
            ))
