from modules.file_processing.parsers.base import FileParser


class TextParser(FileParser):
    async def parse(self, file_bytes: bytes, filename: str) -> str:
        return file_bytes.decode("utf-8", errors="replace")
