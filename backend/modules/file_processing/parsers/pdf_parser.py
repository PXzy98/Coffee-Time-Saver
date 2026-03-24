import fitz  # PyMuPDF
from modules.file_processing.parsers.base import FileParser


class PyMuPDFParser(FileParser):
    async def parse(self, file_bytes: bytes, filename: str) -> str:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        pages = []
        for page in doc:
            pages.append(page.get_text())
        doc.close()
        return "\n\n".join(pages)
