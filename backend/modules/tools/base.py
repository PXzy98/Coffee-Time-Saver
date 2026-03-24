from abc import abstractmethod
from modules.base import BaseModule


class BaseTool(BaseModule):
    """All tool modules extend this."""

    @abstractmethod
    async def execute(self, payload: dict, user_id: str) -> dict:
        """Execute the tool with the given payload and return the result."""
