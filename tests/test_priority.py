"""Tests for the priority scorer."""

import pytest
from src.priority import calculate_priority


def test_critical_priority():
    """Legal threat + safety hazard should score critical."""
    text = "I will sue you. This fire hazard product nearly killed me. I'm calling my lawyer."
    result = calculate_priority(
        complaint_text=text,
        sentiment_polarity=-0.9,
        category="product_quality",
        cluster_size=10,
    )
    assert result["priority_level"] == "critical"
    assert result["priority_score"] >= 80


def test_low_priority():
    """Mild, positive, lone complaint should be low."""
    result = calculate_priority(
        complaint_text="The delivery was a day late but otherwise fine.",
        sentiment_polarity=0.3,
        category="delivery",
        cluster_size=1,
    )
    assert result["priority_level"] in ("low", "medium")


def test_score_in_range():
    result = calculate_priority(
        complaint_text="My refund is pending.",
        sentiment_polarity=-0.2,
        category="refund",
        cluster_size=3,
    )
    assert 0 <= result["priority_score"] <= 100


def test_breakdown_keys():
    result = calculate_priority(
        complaint_text="Product is broken.",
        sentiment_polarity=-0.5,
        category="product_quality",
    )
    bd = result["breakdown"]
    assert "sentiment_pts" in bd
    assert "category_pts" in bd
    assert "urgency_pts" in bd
    assert "cluster_pts" in bd


def test_cluster_size_increases_score():
    base = calculate_priority("Late delivery.", -0.3, "delivery", cluster_size=1)
    large = calculate_priority("Late delivery.", -0.3, "delivery", cluster_size=20)
    assert large["priority_score"] > base["priority_score"]
