from abc import ABC, abstractmethod
from datetime import date

from core.models import Task, User

SOURCE_WEIGHTS = {
    "email": 3,
    "briefing": 2,
    "meeting": 2,
    "manual": 1,
}


class TaskSorterStrategy(ABC):
    @abstractmethod
    async def sort(self, tasks: list[Task], user: User) -> list[Task]:
        """Return tasks sorted by importance (highest first)."""


class HardcodedSorter(TaskSorterStrategy):
    """Phase 1: Sort by priority desc, due_date asc, source weight desc."""

    async def sort(self, tasks: list[Task], user: User) -> list[Task]:
        def key(t: Task):
            due = t.due_date or date.max
            return (-t.priority, due, -SOURCE_WEIGHTS.get(t.source, 0))

        sorted_tasks = sorted(tasks, key=key)
        # Write sort_score back to each task
        total = len(sorted_tasks)
        for rank, task in enumerate(sorted_tasks):
            task.sort_score = (total - rank) / total
        return sorted_tasks


class LLMSorter(TaskSorterStrategy):
    """Phase 2: LLM-evaluated priority ranking."""

    def __init__(self, llm_gateway):
        self.llm = llm_gateway

    async def sort(self, tasks: list[Task], user: User) -> list[Task]:
        import json
        from modules.llm_gateway.schemas import LLMRequest, Message

        task_list = [
            {"id": str(t.id), "title": t.title, "priority": t.priority,
             "due_date": str(t.due_date) if t.due_date else None, "source": t.source}
            for t in tasks
        ]
        request = LLMRequest(
            messages=[
                Message(role="system", content=(
                    "You are a project management assistant. "
                    "Rank the following tasks from most to least important. "
                    "Return a JSON array of task IDs in order of importance."
                )),
                Message(role="user", content=json.dumps(task_list)),
            ],
            config_name="primary",
            response_format="json",
            max_tokens=500,
        )
        response = await self.llm.complete(request)
        try:
            ordered_ids = json.loads(response.content)
            task_map = {str(t.id): t for t in tasks}
            sorted_tasks = [task_map[tid] for tid in ordered_ids if tid in task_map]
            # Add any tasks not in the LLM response at the end
            sorted_tasks += [t for t in tasks if str(t.id) not in ordered_ids]
        except Exception:
            # Fall back to hardcoded sort on LLM failure
            sorted_tasks = await HardcodedSorter().sort(tasks, user)

        total = len(sorted_tasks)
        for rank, task in enumerate(sorted_tasks):
            task.sort_score = (total - rank) / total
        return sorted_tasks


def get_sorter(strategy: str = "hardcoded", llm_gateway=None) -> TaskSorterStrategy:
    if strategy == "llm" and llm_gateway:
        return LLMSorter(llm_gateway)
    return HardcodedSorter()
