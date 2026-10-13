"""
Priority Scorer
===============
Calculates a priority score (0–100) and level for each complaint.

Scoring factors
---------------
1. Sentiment polarity   — more negative = higher score          (0–30 pts)
2. Category weight      — safety/legal topics score higher      (0–25 pts)
3. Urgency keywords     — words that signal immediate risk       (0–25 pts)
4. Cluster size         — large clusters = systemic problem     (0–20 pts)

Priority levels
---------------
 80–100 → critical
 60–79  → high
 40–59  → medium
  0–39  → low
"""

import re

# ── Category base weights ─────────────────────────────────────────────────────

CATEGORY_WEIGHTS: dict[str, float] = {
    "product_quality": 25.0,   # safety hazard potential
    "delivery": 20.0,
    "refund": 18.0,
    "customer_service": 15.0,
    "other": 10.0,
}

# ── Urgency keywords & their individual bonus points ─────────────────────────

URGENCY_KEYWORDS: list[tuple[str, float]] = [
    # Legal / regulatory
    ("lawyer",       10.0),
    ("attorney",     10.0),
    ("sue",          10.0),
    ("lawsuit",      10.0),
    ("legal action", 10.0),
    ("consumer protection", 8.0),
    ("escalat",       6.0),
    # Safety
    ("fire hazard",  10.0),
    ("recall",       10.0),
    ("spark",         9.0),
    ("smoke",         8.0),
    ("electric",      5.0),
    ("injury",        9.0),
    ("hurt",          8.0),
    ("hospital",      9.0),
    ("contamina",     9.0),
    ("metal",         7.0),
    # Extreme frustration
    ("theft",         7.0),
    ("fraud",         8.0),
    ("stolen",        7.0),
    ("unacceptable",  4.0),
    ("immediately",   3.0),
    ("urgent",        4.0),
    ("today",         2.0),
]


def _sentiment_score(polarity: float) -> float:
    """
    Convert TextBlob polarity (-1 → +1) to a 0–30 priority contribution.
    Neutral = 15, most negative = 30, most positive = 0.
    """
    # Flip and scale: polarity -1 → score 30, polarity +1 → score 0
    return round((1 - polarity) / 2 * 30, 2)


def _urgency_score(text: str) -> float:
    """Sum urgency keyword bonuses, capped at 25."""
    text_lower = text.lower()
    total = 0.0
    for keyword, bonus in URGENCY_KEYWORDS:
        if re.search(r"\b" + re.escape(keyword), text_lower):
            total += bonus
    return min(total, 25.0)


def _cluster_score(cluster_size: int) -> float:
    """
    Larger clusters indicate a systemic issue → higher urgency.
    Score 0–20, logarithmic scale.
    """
    import math
    if cluster_size <= 1:
        return 0.0
    return round(min(math.log(cluster_size, 2) * 5, 20.0), 2)


def _level(score: float) -> str:
    if score >= 80:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


# ── Public API ────────────────────────────────────────────────────────────────

def calculate_priority(
    complaint_text: str,
    sentiment_polarity: float,
    category: str,
    cluster_size: int = 1,
) -> dict:
    """
    Calculate the priority of a complaint.

    Parameters
    ----------
    complaint_text    : raw complaint string
    sentiment_polarity: TextBlob polarity (-1.0 to +1.0)
    category          : one of delivery / refund / product_quality /
                        customer_service / other
    cluster_size      : number of complaints in the same cluster

    Returns
    -------
    {
        "priority_score": float,         # 0–100
        "priority_level": str,           # critical / high / medium / low
        "breakdown": {
            "sentiment_pts":  float,
            "category_pts":   float,
            "urgency_pts":    float,
            "cluster_pts":    float,
        }
    }
    """
    sentiment_pts = _sentiment_score(sentiment_polarity)
    category_pts  = CATEGORY_WEIGHTS.get(category, 10.0)
    urgency_pts   = _urgency_score(complaint_text)
    cluster_pts   = _cluster_score(cluster_size)

    raw_score = sentiment_pts + category_pts + urgency_pts + cluster_pts
    # Normalise to 0–100 (theoretical max ≈ 100)
    final_score = round(min(raw_score, 100.0), 2)

    return {
        "priority_score": final_score,
        "priority_level": _level(final_score),
        "breakdown": {
            "sentiment_pts": sentiment_pts,
            "category_pts":  category_pts,
            "urgency_pts":   urgency_pts,
            "cluster_pts":   cluster_pts,
        },
    }
