import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config import settings
from core.models import Task, User
from core.exceptions import NotFoundError, ForbiddenError
from modules.tasks.sorter import get_sorter


class TaskService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_tasks(self, user: User) -> list[Task]:
        result = await self.db.execute(
            select(Task)
            .where(Task.user_id == user.id, Task.is_completed == False)
            .order_by(Task.sort_score.desc().nullslast(), Task.created_at.asc())
        )
        return result.scalars().all()

    async def create_task(self, data: dict, user: User) -> list[Task]:
        task = Task(user_id=user.id, **data)
        self.db.add(task)
        await self.db.flush()
        return await self._resort_and_save(user)

    async def update_task(self, task_id: uuid.UUID, data: dict, user: User) -> list[Task]:
        task = await self._get_own_task(task_id, user)
        for key, val in data.items():
            if val is not None:
                setattr(task, key, val)
        if data.get("is_completed") is True and not task.completed_at:
            task.completed_at = datetime.now(timezone.utc)
        return await self._resort_and_save(user)

    async def delete_task(self, task_id: uuid.UUID, user: User) -> None:
        task = await self._get_own_task(task_id, user)
        await self.db.delete(task)
        await self.db.commit()

    async def _resort_and_save(self, user: User) -> list[Task]:
        result = await self.db.execute(
            select(Task).where(Task.user_id == user.id, Task.is_completed == False)
        )
        tasks = result.scalars().all()
        sorter = get_sorter(settings.TASK_SORTER_STRATEGY)
        sorted_tasks = await sorter.sort(tasks, user)
        await self.db.commit()
        return sorted_tasks

    async def _get_own_task(self, task_id: uuid.UUID, user: User) -> Task:
        result = await self.db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        if task is None:
            raise NotFoundError("Task not found")
        if task.user_id != user.id:
            raise ForbiddenError("Access denied")
        return task
