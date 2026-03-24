import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload

from core.models import Project, ProjectMember, User
from core.exceptions import NotFoundError, ForbiddenError


class ProjectService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_for_user(self, user: User) -> list[Project]:
        result = await self.db.execute(
            select(Project)
            .options(selectinload(Project.members))
            .where(
                or_(
                    Project.owner_id == user.id,
                    Project.is_shared == True,
                    Project.id.in_(
                        select(ProjectMember.project_id).where(ProjectMember.user_id == user.id)
                    ),
                )
            )
            .order_by(Project.created_at.desc())
        )
        return result.scalars().unique().all()

    async def get(self, project_id: uuid.UUID, user: User) -> Project:
        result = await self.db.execute(
            select(Project)
            .options(selectinload(Project.members))
            .where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        if project is None:
            raise NotFoundError("Project not found")
        if not self._can_read(project, user):
            raise ForbiddenError("Access denied")
        return project

    async def create(self, data: dict, owner: User) -> Project:
        project = Project(
            owner_id=owner.id,
            name=data["name"],
            description=data.get("description"),
            status=data.get("status", "active"),
            metadata_=data.get("metadata", {}),
        )
        self.db.add(project)
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def update(self, project_id: uuid.UUID, data: dict) -> Project:
        result = await self.db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if project is None:
            raise NotFoundError("Project not found")
        for key, val in data.items():
            if val is not None:
                setattr(project, "metadata_" if key == "metadata" else key, val)
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def set_shared(self, project_id: uuid.UUID, is_shared: bool) -> Project:
        result = await self.db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if project is None:
            raise NotFoundError("Project not found")
        project.is_shared = is_shared
        await self.db.commit()
        await self.db.refresh(project)
        return project

    def _can_read(self, project: Project, user: User) -> bool:
        if project.is_shared:
            return True
        if project.owner_id == user.id:
            return True
        return any(m.user_id == user.id for m in project.members)
