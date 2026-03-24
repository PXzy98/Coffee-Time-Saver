from modules.base import BaseModule
from modules.tasks.router import router as _router


class TasksModule(BaseModule):
    slug = "tasks"
    router = _router

    async def initialize(self) -> None:
        pass

    async def health_check(self) -> dict:
        return {"module": self.slug, "status": "ok"}


module_instance = TasksModule()
