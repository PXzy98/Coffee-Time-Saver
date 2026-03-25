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
        if request.response_format == "json":
            # Disable thinking for JSON-structured calls.
            # Qwen3/deepseek-r1 on Ollama: thinking tokens consume the budget and
            # leave content empty. Two complementary approaches:
            #   1. extra_body think:false  — Ollama API-level flag
            #   2. /no_think in the USER turn — Qwen3 spec says the control token
            #      must appear in a user message, not the system message.
            kwargs["extra_body"] = {"think": False}
            messages = [m.model_dump() for m in request.messages]
            for msg in messages:
                if msg.get("role") == "user":
                    msg["content"] = "/no_think\n" + msg["content"]
                    break
            kwargs["messages"] = messages
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
