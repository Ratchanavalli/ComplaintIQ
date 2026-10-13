"""Tests for the categorisation module."""

import pytest
from src.categorization import categorize


def test_delivery_category():
    text = "My package has been stuck in transit for 10 days with no update."
    result = categorize(text)
    assert result["category"] == "delivery"
    assert result["confidence"] > 0


def test_refund_category():
    text = "I returned the product 3 weeks ago and still haven't received my refund of $50."
    result = categorize(text)
    assert result["category"] == "refund"


def test_quality_category():
    text = "The product broke after two days. Terrible build quality and now it's defective."
    result = categorize(text)
    assert result["category"] == "product_quality"


def test_service_category():
    text = "The support agent was rude and hung up on me after 2 hours on hold."
    result = categorize(text)
    assert result["category"] == "customer_service"


def test_other_category():
    text = "Just wanted to say something."
    result = categorize(text)
    assert result["category"] == "other"
    assert result["confidence"] == 0.0


def test_safety_hazard():
    text = "The electric kettle started sparking and smoking. This is a fire hazard."
    result = categorize(text)
    assert result["category"] == "product_quality"


def test_scores_dict_present():
    result = categorize("The delivery was late and the refund not processed.")
    assert "scores" in result
    assert isinstance(result["scores"], dict)
