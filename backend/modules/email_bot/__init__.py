from modules.base import BaseModule
from fastapi import APIRouter


class EmailBotModule(BaseModule):
    slug = "email_bot"
    router = APIRouter()  # No public endpoints

    async def initialize(self) -> None:
        pass

    async def health_check(self) -> dict:
        return {"module": self.slug, "status": "ok"}


module_instance = EmailBotModule()
