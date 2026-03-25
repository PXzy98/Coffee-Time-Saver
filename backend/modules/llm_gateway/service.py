import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.models import LLMConfig
from modules.llm_gateway.providers.base import LLMProvider
from modules.llm_gateway.providers.openai_provider import OpenAIProvider
from modules.llm_gateway.providers.claude_provider import ClaudeProvider
from modules.llm_gateway.providers.ollama_provider import OllamaProvider
from modules.llm_gateway.schemas import LLMRequest, LLMResponse

logger = logging.getLogger("coffee_time_saver")

_PROVIDERS: dict[str, LLMProvider] = {
    "openai": OpenAIProvider(),
    "claude": ClaudeProvider(),
    "ollama": OllamaProvider(),
}


class LLMGateway:
    """Single interface for all modules to call LLMs."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def complete(self, request: LLMRequest) -> LLMResponse:
        config = await self._get_active_config(request.config_name)
        provider = _PROVIDERS[config.provider]
        logger.info("LLM complete via %s / %s", config.provider, config.model)
        return await provider.complete(request, config)

    async def embed(self, texts: list[str], config_name: str = "embedding") -> list[list[float]]:
        config = await self._get_active_config(config_name)
        provider = _PROVIDERS[config.provider]
        return await provider.embed(texts, config)

    async def _get_active_config(self, name: str) -> LLMConfig:
        # Try exact name match first
        result = await self.db.execute(
            select(LLMConfig).where(LLMConfig.name == name, LLMConfig.is_active == True)
        )
        config = result.scalar_one_or_none()
        if config is not None:
            return config
        # Fall back to any active config
        result = await self.db.execute(
            select(LLMConfig).where(LLMConfig.is_active == True).limit(1)
        )
        config = result.scalar_one_or_none()
        if config is None:
            raise ValueError("No active LLM config found. Configure one in Settings → LLM.")
        logger.info("LLM config '%s' not found, using '%s' instead", name, config.name)
        return config
