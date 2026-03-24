from openai import AsyncOpenAI
from modules.llm_gateway.providers.base import LLMProvider
from modules.llm_gateway.schemas import LLMRequest, LLMResponse, TokenUsage


class OpenAIProvider(LLMProvider):
    async def complete(self, request: LLMRequest, config) -> LLMResponse:
        client = AsyncOpenAI(api_key=config.api_key, base_url=config.api_url)
        kwargs = dict(
            model=config.model,
            messages=[m.model_dump() for m in request.messages],
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
        if request.response_format == "json":
            kwargs["response_format"] = {"type": "json_object"}
        if request.tools:
            kwargs["tools"] = request.tools

        response = await client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        content = choice.message.content or ""
        # If tool_calls returned, serialize them as content for caller to handle
        if choice.message.tool_calls:
            import json
            content = json.dumps([tc.model_dump() for tc in choice.message.tool_calls])

        usage = response.usage
        return LLMResponse(
            content=content,
            usage=TokenUsage(
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
                total_tokens=usage.total_tokens if usage else 0,
            ),
            model=config.model,
            provider="openai",
        )

    async def embed(self, texts: list[str], config) -> list[list[float]]:
        client = AsyncOpenAI(api_key=config.api_key, base_url=config.api_url)
        response = await client.embeddings.create(input=texts, model=config.model)
        return [item.embedding for item in response.data]
