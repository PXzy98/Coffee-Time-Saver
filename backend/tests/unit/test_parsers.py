"""Unit tests for file parsers — no database required."""
import pytest
import asyncio
from modules.file_processing.parsers.text_parser import TextParser
from modules.file_processing.parsers.pdf_parser import PyMuPDFParser


@pytest.mark.asyncio
async def test_text_parser_utf8():
    parser = TextParser()
    result = await parser.parse(b"Hello, world!", "test.txt")
    assert result == "Hello, world!"


@pytest.mark.asyncio
async def test_text_parser_utf8_french():
    parser = TextParser()
    content = "Bonjour le monde! Réunion à 14h."
    result = await parser.parse(content.encode("utf-8"), "test.txt")
    assert "Bonjour" in result


@pytest.mark.asyncio
async def test_text_parser_invalid_bytes_replaced():
    parser = TextParser()
    result = await parser.parse(b"Hello \xff world", "test.txt")
    assert "Hello" in result
    assert "world" in result


@pytest.mark.asyncio
async def test_pdf_parser_creates_text(tmp_path):
    """Create a minimal PDF in memory and parse it."""
    pytest.importorskip("fitz")
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Test document content for parsing.")
    pdf_bytes = doc.tobytes()
    doc.close()

    parser = PyMuPDFParser()
    result = await parser.parse(pdf_bytes, "test.pdf")
    assert "Test document content" in result
