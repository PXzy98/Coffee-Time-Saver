import uuid
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel


class BriefingOut(BaseModel):
    id: uuid.UUID
    date: date
    content_en: Optional[str]
    content_fr: Optional[str]
    generated_at: datetime

    model_config = {"from_attributes": True}
