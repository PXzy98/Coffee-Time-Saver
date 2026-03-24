from langdetect import detect, LangDetectException


def detect_language(text: str) -> str:
    """Detect language of text. Returns 'en' or 'fr', defaults to 'en' on failure."""
    if not text or len(text.strip()) < 20:
        return "en"
    try:
        lang = detect(text)
        return lang if lang in ("en", "fr") else "en"
    except LangDetectException:
        return "en"
