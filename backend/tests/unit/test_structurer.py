"""Unit tests for text structurer — no database required."""
import pytest
from modules.ingestion.structurer import RegexStructurer


@pytest.mark.asyncio
async def test_extracts_iso_dates():
    structurer = RegexStructurer()
    text = "The project kicked off on 2024-03-15 and ends on 2024-12-31."
    result = await structurer.structure(text)
    assert "2024-03-15" in result["dates_mentioned"]
    assert "2024-12-31" in result["dates_mentioned"]


@pytest.mark.asyncio
async def test_extracts_action_items():
    structurer = RegexStructurer()
    text = "Action item: review the scope document. Todo: update the timeline."
    result = await structurer.structure(text)
    assert len(result["action_items"]) >= 1


@pytest.mark.asyncio
async def test_empty_text_returns_empty_lists():
    structurer = RegexStructurer()
    result = await structurer.structure("")
    assert result["dates_mentioned"] == []
    assert result["action_items"] == []


@pytest.mark.asyncio
async def test_no_false_positives():
    structurer = RegexStructurer()
    text = "This text has no dates or action items in it."
    result = await structurer.structure(text)
    assert result["dates_mentioned"] == []
    assert result["action_items"] == []
