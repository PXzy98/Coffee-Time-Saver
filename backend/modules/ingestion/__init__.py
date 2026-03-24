from modules.base import BaseModule
from fastapi import APIRouter


class IngestionModule(BaseModule):
    slug = "ingestion"
    router = APIRouter()  # No public endpoints

    async def initialize(self) -> None:
        pass

    async def health_check(self) -> dict:
        return {"module": self.slug, "status": "ok"}


module_instance = IngestionModule()
