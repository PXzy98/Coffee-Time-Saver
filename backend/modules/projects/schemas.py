import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    status: str = "active"
    metadata: dict = {}


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    metadata: Optional[dict] = None


class MemberOut(BaseModel):
    user_id: uuid.UUID
    role: str

    model_config = {"from_attributes": True}


class ProjectOut(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    status: str
    owner_id: Optional[uuid.UUID]
    is_shared: bool
    metadata: dict
    created_at: datetime
    members: list[MemberOut] = []

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_project(cls, project):
        return cls(
            id=project.id,
            name=project.name,
            description=project.description,
            status=project.status,
            owner_id=project.owner_id,
            is_shared=project.is_shared,
            metadata=project.metadata_,
            created_at=project.created_at,
            members=[MemberOut(user_id=m.user_id, role=m.role) for m in project.members],
        )
