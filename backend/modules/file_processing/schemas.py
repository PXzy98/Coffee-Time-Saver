import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: uuid.UUID
    filename: str
    mime_type: Optional[str]
    file_size_bytes: Optional[int]
    status: str
    source: str
    doc_type: str
    project_id: Optional[uuid.UUID]
    created_at: datetime

    model_config = {"from_attributes": True}


class UploadResponse(BaseModel):
    document_id: uuid.UUID
    filename: str
    status: str
    message: str
