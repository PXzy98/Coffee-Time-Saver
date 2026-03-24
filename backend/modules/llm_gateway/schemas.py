from typing import Optional
from pydantic import BaseModel


class Message(BaseModel):
    role: str  # "system", "user", "assistant"
    content: str


class LLMRequest(BaseModel):
    messages: list[Message]
    config_name: str = "primary"
    temperature: float = 0.7
    max_tokens: int = 2000
    response_format: Optional[str] = None  # "json" for structured output
    tools: Optional[list[dict]] = None     # for function calling / tool use


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class LLMResponse(BaseModel):
    content: str
    usage: TokenUsage
    model: str
    provider: str
