import json
import anthropic
from modules.llm_gateway.providers.base import LLMProvider
from modules.llm_gateway.schemas import LLMRequest, LLMResponse, TokenUsage


class ClaudeProvider(LLMProvider):
    async def complete(self, request: LLMRequest, config) -> LLMResponse:
        client = anthropic.AsyncAnthropic(api_key=config.api_key, base_url=config.api_url)

        # Separate system message from conversation
        system = ""
        messages = []
        for m in request.messages:
            if m.role == "system":
                system = m.content
            else:
                messages.append({"role": m.role, "content": m.content})

        kwargs = dict(
            model=config.model,
            max_tokens=request.max_tokens,
            messages=messages,
        )
        if system:
            kwargs["system"] = system
        if request.tools:
            kwargs["tools"] = request.tools

        response = await client.messages.create(**kwargs)

        content = ""
        for block in response.content:
            if block.type == "text":
                content = block.text
            elif block.type == "tool_use":
                content = json.dumps({"type": "tool_use", "name": block.name, "input": block.input})

        usage = response.usage
        return LLMResponse(
            content=content,
            usage=TokenUsage(
                prompt_tokens=usage.input_tokens if usage else 0,
                completion_tokens=usage.output_tokens if usage else 0,
                total_tokens=(usage.input_tokens + usage.output_tokens) if usage else 0,
            ),
            model=config.model,
            provider="claude",
        )

    async def embed(self, texts: list[str], config) -> list[list[float]]:
        # Anthropic does not currently have a public embeddings API;
        # fall back to a zero vector as a graceful stub.
        return [[0.0] * 1536 for _ in texts]
