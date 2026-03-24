from modules.base import BaseModule
from modules.file_processing.router import router as _router
from fastapi import APIRouter


class FileProcessingModule(BaseModule):
    slug = "file_processing"
    router = _router

    async def initialize(self) -> None:
        pass

    async def health_check(self) -> dict:
        return {"module": self.slug, "status": "ok"}


module_instance = FileProcessingModule()
