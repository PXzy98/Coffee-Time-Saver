import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.auth.dependencies import get_current_user
from core.models import User
from core.logging import audit_log
from core.websocket import manager
from modules.tasks.schemas import TaskCreate, TaskUpdate, TaskOut
from modules.tasks.service import TaskService

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskOut])
async def list_tasks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = TaskService(db)
    return await service.list_tasks(current_user)


@router.post("", response_model=list[TaskOut], status_code=201)
async def create_task(
    body: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = TaskService(db)
    tasks = await service.create_task(body.model_dump(), current_user)
    await audit_log(db, action="task.create", entity_type="task", user_id=current_user.id)
    await manager.publish(current_user.id, {"type": "task.updated", "payload": {"tasks": [str(t.id) for t in tasks]}})
    return tasks


@router.patch("/{task_id}", response_model=list[TaskOut])
async def update_task(
    task_id: uuid.UUID,
    body: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = TaskService(db)
    tasks = await service.update_task(task_id, body.model_dump(exclude_none=True), current_user)
    await audit_log(db, action="task.update", entity_type="task", entity_id=str(task_id), user_id=current_user.id)
    await manager.publish(current_user.id, {"type": "task.updated", "payload": {}})
    return tasks


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = TaskService(db)
    await service.delete_task(task_id, current_user)
    await audit_log(db, action="task.delete", entity_type="task", entity_id=str(task_id), user_id=current_user.id)
