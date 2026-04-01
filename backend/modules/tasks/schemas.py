import uuid
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: int = 50
    due_date: Optional[date] = None
    scheduled_at: Optional[datetime] = None
    project_id: Optional[uuid.UUID] = None
    source: str = "manual"


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[int] = None
    due_date: Optional[date] = None
    scheduled_at: Optional[datetime] = None
    is_completed: Optional[bool] = None
    project_id: Optional[uuid.UUID] = None


class TaskOut(BaseModel):
    id: uuid.UUID
    title: str
    description: Optional[str]
    priority: int
    due_date: Optional[date]
    scheduled_at: Optional[datetime]
    is_completed: bool
    completed_at: Optional[datetime]
    source: str
    sort_score: Optional[float]
    project_id: Optional[uuid.UUID]
    created_at: datetime

    model_config = {"from_attributes": True}
