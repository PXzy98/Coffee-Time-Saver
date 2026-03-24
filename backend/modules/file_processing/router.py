import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from core.auth.dependencies import get_current_user
from core.models import User, Document
from core.logging import audit_log
from modules.file_processing.schemas import DocumentOut, UploadResponse
from modules.file_processing.service import _get_parser

router = APIRouter(prefix="/api/files", tags=["files"])

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "text/csv",
    "text/plain",
    "text/markdown",
}


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_file(
    file: UploadFile = File(...),
    project_id: Optional[uuid.UUID] = Form(None),
    doc_type: str = Form("general"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    content_type = file.content_type or ""
    if content_type not in ALLOWED_MIME_TYPES and not file.filename.endswith((".txt", ".md", ".csv")):
        raise HTTPException(status_code=415, detail=f"Unsupported file type: {content_type}")

    file_bytes = await file.read()

    # Parse immediately so full_text is available for ingestion
    parser = _get_parser(content_type, file.filename)
    full_text = await parser.parse(file_bytes, file.filename)

    doc = Document(
        project_id=project_id,
        uploaded_by=current_user.id,
        filename=file.filename,
        mime_type=content_type,
        file_size_bytes=len(file_bytes),
        full_text=full_text,
        status="pending",
        source="upload",
        doc_type=doc_type,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Dispatch Celery task — original bytes are NOT stored; full_text is already in DB
    from tasks.file_tasks import process_file
    process_file.delay(str(doc.id))

    await audit_log(db, action="file.upload", entity_type="document", entity_id=str(doc.id),
                    user_id=current_user.id, details={"filename": file.filename, "size": len(file_bytes)})

    return UploadResponse(
        document_id=doc.id,
        filename=doc.filename,
        status=doc.status,
        message="File uploaded and queued for processing.",
    )


@router.get("", response_model=list[DocumentOut])
async def list_files(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Document)
        .where(Document.uploaded_by == current_user.id)
        .order_by(Document.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{document_id}/status")
async def file_status(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.uploaded_by == current_user.id)
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"document_id": str(doc.id), "status": doc.status}
