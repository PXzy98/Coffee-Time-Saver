"""
Integration tests for the Tasks service.
Requires: TEST_DATABASE_URL=postgresql+asyncpg://cts:cts_password@localhost:5432/cts_test
"""
import pytest
import pytest_asyncio
from modules.tasks.service import TaskService


@pytest.mark.asyncio
async def test_create_and_list_task(db_session, seeded_db):
    user = seeded_db["user"]
    service = TaskService(db_session)

    tasks = await service.create_task(
        {"title": "Write tests", "priority": 80, "source": "manual"},
        user,
    )
    assert len(tasks) == 1
    assert tasks[0].title == "Write tests"
    assert tasks[0].sort_score is not None


@pytest.mark.asyncio
async def test_complete_task(db_session, seeded_db):
    user = seeded_db["user"]
    service = TaskService(db_session)

    await service.create_task({"title": "Task A", "priority": 50}, user)
    tasks_before = await service.list_tasks(user)
    assert len(tasks_before) == 1

    task_id = tasks_before[0].id
    remaining = await service.update_task(task_id, {"is_completed": True}, user)
    assert len(remaining) == 0  # completed tasks not in active list


@pytest.mark.asyncio
async def test_delete_task(db_session, seeded_db):
    user = seeded_db["user"]
    service = TaskService(db_session)

    await service.create_task({"title": "To delete", "priority": 50}, user)
    tasks = await service.list_tasks(user)
    task_id = tasks[0].id

    await service.delete_task(task_id, user)
    assert await service.list_tasks(user) == []


@pytest.mark.asyncio
async def test_sort_score_ordering(db_session, seeded_db):
    from datetime import date, timedelta
    user = seeded_db["user"]
    service = TaskService(db_session)

    await service.create_task({"title": "Low priority", "priority": 10}, user)
    await service.create_task({"title": "High priority", "priority": 90}, user)
    tasks = await service.list_tasks(user)

    assert tasks[0].title == "High priority"
    assert tasks[0].sort_score > tasks[1].sort_score
