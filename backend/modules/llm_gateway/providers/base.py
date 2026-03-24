from abc import ABC, abstractmethod
from modules.llm_gateway.schemas import LLMRequest, LLMResponse


class LLMProvider(ABC):
    @abstractmethod
    async def complete(self, request: LLMRequest, config: "LLMConfig") -> LLMResponse:
        """Send a completion request and return a unified LLMResponse."""

    @abstractmethod
    async def embed(self, texts: list[str], config: "LLMConfig") -> list[list[float]]:
        """Generate embeddings for a list of texts."""
