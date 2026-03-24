from modules.base import BaseModule
from modules.dashboard.router import router as _router


class DashboardModule(BaseModule):
    slug = "dashboard"
    router = _router

    async def initialize(self) -> None:
        pass

    async def health_check(self) -> dict:
        return {"module": self.slug, "status": "ok"}


module_instance = DashboardModule()
