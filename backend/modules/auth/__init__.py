from fastapi import APIRouter
from modules.base import BaseModule
from modules.auth.router import router as _router


class AuthModule(BaseModule):
    slug = "auth"
    router = _router

    async def initialize(self) -> None:
        pass

    async def health_check(self) -> dict:
        return {"module": self.slug, "status": "ok"}


module_instance = AuthModule()
