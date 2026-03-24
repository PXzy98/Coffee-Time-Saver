from modules.base import BaseModule
from modules.llm_gateway.service import LLMGateway
from fastapi import APIRouter


class LLMGatewayModule(BaseModule):
    slug = "llm_gateway"
    router = APIRouter()  # No public endpoints; used internally

    async def initialize(self) -> None:
        pass

    async def health_check(self) -> dict:
        return {"module": self.slug, "status": "ok"}


module_instance = LLMGatewayModule()
