"""Unit tests for language detection — no database required."""
import pytest
from modules.ingestion.language_detect import detect_language


def test_english_text():
    text = "The project deadline is next Friday. Please review the attached documents."
    assert detect_language(text) == "en"


def test_french_text():
    text = "La réunion est prévue pour vendredi prochain. Veuillez examiner les documents joints."
    assert detect_language(text) == "fr"


def test_short_text_defaults_to_en():
    assert detect_language("hi") == "en"


def test_empty_text_defaults_to_en():
    assert detect_language("") == "en"


def test_unknown_language_falls_back_to_en():
    # Chinese text — not en or fr, should default to "en"
    result = detect_language("这是一段中文文本，用于测试语言检测功能。")
    assert result == "en"
