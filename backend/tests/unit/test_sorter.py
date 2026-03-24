"""Unit tests for task sorter strategies — no database required."""
import uuid
import pytest
from datetime import date, timedelta
from unittest.mock import MagicMock

from modules.tasks.sorter import HardcodedSorter, SOURCE_WEIGHTS
from core.models import Task, User


def _make_task(priority=50, due_offset_days=None, source="manual") -> Task:
    t = Task()
    t.id = uuid.uuid4()
    t.priority = priority
    t.due_date = (date.today() + timedelta(days=due_offset_days)) if due_offset_days is not None else None
    t.source = source
    t.sort_score = None
    return t


def _make_user() -> User:
    u = User()
    u.id = uuid.uuid4()
    return u


@pytest.mark.asyncio
async def test_hardcoded_sorter_priority_order():
    sorter = HardcodedSorter()
    user = _make_user()
    tasks = [
        _make_task(priority=10),
        _make_task(priority=90),
        _make_task(priority=50),
    ]
    result = await sorter.sort(tasks, user)
    assert result[0].priority == 90
    assert result[-1].priority == 10


@pytest.mark.asyncio
async def test_hardcoded_sorter_due_date_order():
    sorter = HardcodedSorter()
    user = _make_user()
    tasks = [
        _make_task(priority=50, due_offset_days=10),
        _make_task(priority=50, due_offset_days=1),
        _make_task(priority=50, due_offset_days=5),
    ]
    result = await sorter.sort(tasks, user)
    assert result[0].due_date == tasks[1].due_date  # due in 1 day first


@pytest.mark.asyncio
async def test_hardcoded_sorter_source_weight():
    sorter = HardcodedSorter()
    user = _make_user()
    tasks = [
        _make_task(priority=50, source="manual"),
        _make_task(priority=50, source="email"),
    ]
    result = await sorter.sort(tasks, user)
    assert result[0].source == "email"  # email has higher source weight


@pytest.mark.asyncio
async def test_sort_scores_assigned():
    sorter = HardcodedSorter()
    user = _make_user()
    tasks = [_make_task() for _ in range(5)]
    result = await sorter.sort(tasks, user)
    scores = [t.sort_score for t in result]
    assert all(s is not None for s in scores)
    assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_empty_task_list():
    sorter = HardcodedSorter()
    user = _make_user()
    result = await sorter.sort([], user)
    assert result == []
