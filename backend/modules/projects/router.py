import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.auth.dependencies import get_current_user, require_role
from core.models import User
from core.logging import audit_log
from modules.projects.schemas import ProjectCreate, ProjectUpdate, ProjectOut
from modules.projects.service import ProjectService

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=list[ProjectOut])
async def list_projects(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ProjectService(db)
    projects = await service.list_for_user(current_user)
    return [ProjectOut.from_orm_project(p) for p in projects]


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ProjectService(db)
    project = await service.get(project_id, current_user)
    return ProjectOut.from_orm_project(project)


@router.post("", response_model=ProjectOut, status_code=201)
async def create_project(
    body: ProjectCreate,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    service = ProjectService(db)
    project = await service.create(body.model_dump(), current_user)
    await audit_log(db, action="project.create", entity_type="project", entity_id=str(project.id),
                    user_id=current_user.id)
    return ProjectOut.from_orm_project(project)


@router.patch("/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: uuid.UUID,
    body: ProjectUpdate,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    service = ProjectService(db)
    project = await service.update(project_id, body.model_dump(exclude_none=True))
    await audit_log(db, action="project.update", entity_type="project", entity_id=str(project_id),
                    user_id=current_user.id)
    return ProjectOut.from_orm_project(project)


@router.patch("/{project_id}/share", response_model=ProjectOut)
async def toggle_share(
    project_id: uuid.UUID,
    is_shared: bool,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    service = ProjectService(db)
    project = await service.set_shared(project_id, is_shared)
    await audit_log(db, action="project.share_toggle", entity_type="project",
                    entity_id=str(project_id), user_id=current_user.id,
                    details={"is_shared": is_shared})
    return ProjectOut.from_orm_project(project)
