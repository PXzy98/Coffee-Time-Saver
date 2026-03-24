from abc import ABC, abstractmethod


class FileParser(ABC):
    @abstractmethod
    async def parse(self, file_bytes: bytes, filename: str) -> str:
        """Extract plain text from raw file bytes. Returns the full text."""
