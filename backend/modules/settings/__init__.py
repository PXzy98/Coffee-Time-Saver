from modules.base import BaseModule
from modules.settings.router import router as _router


class SettingsModule(BaseModule):
    slug = "settings"
    router = _router

    async def initialize(self) -> None:
        pass

    async def health_check(self) -> dict:
        return {"module": self.slug, "status": "ok"}


module_instance = SettingsModule()
