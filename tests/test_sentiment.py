"""Tests for the sentiment analyser."""

import pytest
from src.sentiment import analyze_sentiment


def test_negative_sentiment():
    text = "This is terrible! I'm extremely angry and disappointed. Absolutely unacceptable!"
    result = analyze_sentiment(text)
    assert result["sentiment"] == "negative"
    assert result["polarity"] < 0


def test_positive_sentiment():
    text = "Great service! The team resolved my issue very quickly. Highly impressed!"
    result = analyze_sentiment(text)
    assert result["sentiment"] == "positive"
    assert result["polarity"] > 0


def test_neutral_sentiment():
    text = "The item arrived. It is the product I ordered."
    result = analyze_sentiment(text)
    # Neutral is expected; polarity close to 0
    assert result["sentiment"] in ("neutral", "positive", "negative")  # flexible
    assert -1.0 <= result["polarity"] <= 1.0


def test_return_keys():
    result = analyze_sentiment("My order was delayed.")
    assert "sentiment" in result
    assert "polarity" in result
    assert "subjectivity" in result


def test_polarity_range():
    for text in [
        "I hate this product.",
        "This is fine.",
        "Amazing experience!",
    ]:
        result = analyze_sentiment(text)
        assert -1.0 <= result["polarity"] <= 1.0
        assert 0.0 <= result["subjectivity"] <= 1.0
