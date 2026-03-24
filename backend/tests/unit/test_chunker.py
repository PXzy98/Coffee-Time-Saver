"""Unit tests for text chunker — no database required."""
import pytest
from modules.ingestion.chunker import chunk_text


def test_empty_text():
    assert chunk_text("") == []


def test_short_text_single_chunk():
    result = chunk_text("hello world", chunk_size=100)
    assert len(result) == 1
    assert result[0] == "hello world"


def test_chunks_overlap():
    # 10 words, chunk_size=6, overlap=2 → windows at 0 and 4
    words = list(range(10))
    text = " ".join(str(w) for w in words)
    chunks = chunk_text(text, chunk_size=6, overlap=2)
    assert len(chunks) == 2
    # Second chunk should start 4 words in (chunk_size - overlap = 4)
    assert chunks[1].startswith("4 5")


def test_exact_chunk_size():
    text = " ".join(["word"] * 1000)
    chunks = chunk_text(text, chunk_size=1000, overlap=200)
    assert len(chunks) == 1


def test_large_text_produces_multiple_chunks():
    text = " ".join(["word"] * 2500)
    chunks = chunk_text(text, chunk_size=1000, overlap=200)
    # 2500 words: chunk 1 → 0-1000, chunk 2 → 800-1800, chunk 3 → 1600-2500
    assert len(chunks) == 3
