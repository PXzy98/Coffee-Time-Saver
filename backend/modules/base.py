from abc import ABC, abstractmethod
from fastapi import APIRouter


class BaseModule(ABC):
    """All backend modules extend this."""

    @property
    @abstractmethod
    def slug(self) -> str:
        """Unique identifier, e.g. 'tasks', 'risk-analyzer'."""

    @property
    @abstractmethod
    def router(self) -> APIRouter:
        """FastAPI router with this module's endpoints."""

    @abstractmethod
    async def initialize(self) -> None:
        """Called on app startup. Load config, warm caches, etc."""

    @abstractmethod
    async def health_check(self) -> dict:
        """Return module health status."""
