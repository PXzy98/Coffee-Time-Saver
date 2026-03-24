import re
from abc import ABC, abstractmethod
from typing import Optional


class TextStructurer(ABC):
    @abstractmethod
    async def structure(self, text: str) -> dict:
        """Extract structured data from a text chunk."""


class RegexStructurer(TextStructurer):
    """Phase 1: Rule-based extraction of dates, action items, and keywords."""

    _DATE_RE = re.compile(
        r"\b(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}|"
        r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4})\b",
        re.IGNORECASE,
    )
    _ACTION_RE = re.compile(
        r"(?:action item|todo|follow.up|next step|assigned to|action required)[:\s]+(.+?)(?:\.|$)",
        re.IGNORECASE,
    )

    async def structure(self, text: str) -> dict:
        dates = list(set(self._DATE_RE.findall(text)))
        actions = [m.group(1).strip() for m in self._ACTION_RE.finditer(text)]
        return {
            "dates_mentioned": dates[:10],
            "action_items": actions[:10],
        }


class LLMStructurer(TextStructurer):
    """Future: LLM-based structured extraction (Phase 2 upgrade)."""

    def __init__(self, llm_gateway):
        self.llm = llm_gateway

    async def structure(self, text: str) -> dict:
        from modules.llm_gateway.schemas import LLMRequest, Message
        request = LLMRequest(
            messages=[
                Message(role="system", content=(
                    "Extract structured data from the following text. "
                    "Return JSON with keys: dates_mentioned (list), action_items (list), "
                    "entities (list of names/orgs), summary (1-2 sentences)."
                )),
                Message(role="user", content=text[:3000]),
            ],
            config_name="primary",
            response_format="json",
            max_tokens=500,
        )
        import json
        response = await self.llm.complete(request)
        try:
            return json.loads(response.content)
        except Exception:
            return {}


def get_structurer(strategy: str = "regex", llm_gateway=None) -> TextStructurer:
    if strategy == "llm" and llm_gateway:
        return LLMStructurer(llm_gateway)
    return RegexStructurer()
