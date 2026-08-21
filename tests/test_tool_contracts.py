"""Tests for normalized agent tool responses."""

from app.agents.tools import tool_guidance_tracker, tool_sentiment


def test_unimplemented_sentiment_is_not_reported_as_success():
    result = tool_sentiment.invoke({"text": "Management expects growth"})
    assert result["status"] == "not_supported"
    assert result["success"] is False
    assert result["confidence"] == 0.0


def test_unimplemented_guidance_is_not_reported_as_success():
    result = tool_guidance_tracker.invoke({"stock_code": "2330", "period": "2025Q1"})
    assert result["status"] == "not_supported"
    assert result["success"] is False
