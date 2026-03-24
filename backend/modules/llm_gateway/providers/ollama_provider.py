from openai import AsyncOpenAI
from modules.llm_gateway.providers.base import LLMProvider
from modules.llm_gateway.schemas import LLMRequest, LLMResponse, TokenUsage


class OllamaProvider(LLMProvider):
    """Ollama exposes an OpenAI-compatible API at /v1."""

    async def complete(self, request: LLMRequest, config) -> LLMResponse:
        client = AsyncOpenAI(api_key="ollama", base_url=config.api_url)
        kwargs = dict(
            model=config.model,
            messages=[m.model_dump() for m in request.messages],
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
        response = await client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        usage = response.usage
        return LLMResponse(
            content=choice.message.content or "",
            usage=TokenUsage(
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
                total_tokens=usage.total_tokens if usage else 0,
            ),
            model=config.model,
            provider="ollama",
        )

    async def embed(self, texts: list[str], config) -> list[list[float]]:
        client = AsyncOpenAI(api_key="ollama", base_url=config.api_url)
        response = await client.embeddings.create(input=texts, model=config.model)
        return [item.embedding for item in response.data]
