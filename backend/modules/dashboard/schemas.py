from typing import Optional
from pydantic import BaseModel
import uuid
from datetime import datetime


class MetricsOut(BaseModel):
    active_projects: int
    overdue_tasks: int
    pending_tasks: int
    files_processed_today: int
    unread_emails: int


class ActivityItem(BaseModel):
    action: str
    entity_type: Optional[str]
    entity_id: Optional[str]
    created_at: datetime


class DashboardOut(BaseModel):
    metrics: MetricsOut
    recent_activity: list[ActivityItem]
