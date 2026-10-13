"""Tests for the clustering module."""

import pytest
from src.grouping import cluster_complaints, build_cluster_label


DELIVERY_COMPLAINTS = [
    "My package has not arrived after 10 days.",
    "The parcel is stuck in transit and tracking shows no update.",
    "I never received my shipment. Courier says delivered but it wasn't.",
    "Order dispatched 2 weeks ago still not here.",
    "Package was delivered to wrong address.",
]

REFUND_COMPLAINTS = [
    "I want my money back for the returned item.",
    "Refund still pending after 30 days.",
    "I was charged twice and need a reimbursement.",
]


def test_returns_correct_structure():
    result = cluster_complaints(DELIVERY_COMPLAINTS)
    assert "labels" in result
    assert "n_clusters" in result
    assert "top_terms" in result
    assert "sizes" in result


def test_label_count_matches_input():
    texts = DELIVERY_COMPLAINTS + REFUND_COMPLAINTS
    result = cluster_complaints(texts)
    assert len(result["labels"]) == len(texts)


def test_single_complaint():
    result = cluster_complaints(["Only one complaint here."])
    assert result["n_clusters"] == 1
    assert result["labels"] == [0]


def test_cluster_label_builder():
    label = build_cluster_label(["delivery", "package", "late"], "delivery")
    assert "Delivery" in label
    assert "delivery" in label or "package" in label or "late" in label


def test_two_distinct_groups():
    texts = DELIVERY_COMPLAINTS + REFUND_COMPLAINTS
    result = cluster_complaints(texts, n_clusters=2)
    assert result["n_clusters"] == 2
    # Each cluster has at least one member
    assert all(v >= 1 for v in result["sizes"].values())
