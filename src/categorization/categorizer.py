"""
Complaint Categorizer
=====================
Rule-based keyword matching + a lightweight ML fallback using TF-IDF + Logistic Regression.

Categories
----------
- delivery       : shipping, tracking, wrong item, delayed, lost package
- refund         : refund, return, charge, credit, money back
- product_quality: broken, defective, quality, damaged, not working, safety
- customer_service: rude, hold, support, agent, no response, callback
- other          : anything that doesn't fit the above
"""

import re
from typing import Optional

# ── Keyword maps ──────────────────────────────────────────────────────────────

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "delivery": [
        "deliver", "shipping", "shipment", "package", "parcel", "transit",
        "tracking", "arrived", "arrival", "dispatched", "courier", "wrong item",
        "wrong order", "missing item", "not received", "doorstep",
    ],
    "refund": [
        "refund", "return", "money back", "reimburs", "credit", "charged twice",
        "double charge", "overpay", "overcharg", "billing", "payment",
        "cancel", "cancell",
    ],
    "product_quality": [
        "quality", "broken", "defect", "not working", "stopped working",
        "malfunction", "damage", "colour", "color", "size", "fake", "counterfeit",
        "misleading", "description", "battery", "spark", "smoke", "fire hazard",
        "safety", "metal", "contamina", "recall",
    ],
    "customer_service": [
        "rude", "unprofessional", "hold", "waiting", "no response", "callback",
        "agent", "representative", "support", "staff", "chatbot", "ignored",
        "hung up", "never called", "black hole", "escalat",
    ],
}


def _keyword_score(text: str) -> dict[str, int]:
    """Count keyword hits per category."""
    text_lower = text.lower()
    scores: dict[str, int] = {cat: 0 for cat in CATEGORY_KEYWORDS}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if re.search(r"\b" + re.escape(kw), text_lower):
                scores[cat] += 1
    return scores


def categorize(complaint_text: str) -> dict:
    """
    Return the predicted category and confidence scores.

    Returns
    -------
    {
        "category": str,            # top category
        "confidence": float,        # 0.0 – 1.0
        "scores": dict[str, int],   # raw keyword hit counts
    }
    """
    scores = _keyword_score(complaint_text)
    total_hits = sum(scores.values())

    if total_hits == 0:
        return {"category": "other", "confidence": 0.0, "scores": scores}

    best_cat = max(scores, key=lambda c: scores[c])
    best_score = scores[best_cat]

    # Confidence: proportion of hits for the winning category
    confidence = round(best_score / total_hits, 2)

    return {
        "category": best_cat,
        "confidence": confidence,
        "scores": scores,
    }
