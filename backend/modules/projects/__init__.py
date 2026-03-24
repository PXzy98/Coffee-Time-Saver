from modules.base import BaseModule
from modules.projects.router import router as _router


class ProjectsModule(BaseModule):
    slug = "projects"
    router = _router

    async def initialize(self) -> None:
        pass

    async def health_check(self) -> dict:
        return {"module": self.slug, "status": "ok"}


module_instance = ProjectsModule()
