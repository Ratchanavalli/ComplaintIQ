"""
Analysis Pipeline
=================
Orchestrates the four intelligence stages for one or many complaints:

  categorize → analyse sentiment → cluster → score priority

Usage
-----
    from src.utils.pipeline import run_pipeline
    run_pipeline(db_session)          # processes all unanalysed complaints
"""

from sqlalchemy.orm import Session

from src.categorization import categorize
from src.sentiment import analyze_sentiment
from src.priority import calculate_priority
from src.grouping import cluster_complaints, build_cluster_label
from src.db.models import Complaint, Cluster, ProcessingLog


# ── Single complaint ──────────────────────────────────────────────────────────

def analyse_one(complaint: Complaint, db: Session, cluster_size: int = 1) -> Complaint:
    """
    Run all four stages on a single Complaint ORM object and persist results.
    """
    text = complaint.complaint_text

    # 1. Categorisation
    cat_result = categorize(text)
    complaint.category = cat_result["category"]
    _log(db, complaint.id, "categorization", "success",
         f"category={cat_result['category']} confidence={cat_result['confidence']}")

    # 2. Sentiment
    sent_result = analyze_sentiment(text)
    complaint.sentiment = sent_result["sentiment"]
    complaint.sentiment_score = sent_result["polarity"]
    _log(db, complaint.id, "sentiment", "success",
         f"sentiment={sent_result['sentiment']} polarity={sent_result['polarity']}")

    # 3. Priority  (cluster_size refined later after grouping)
    pri_result = calculate_priority(
        complaint_text=text,
        sentiment_polarity=sent_result["polarity"],
        category=cat_result["category"],
        cluster_size=cluster_size,
    )
    complaint.priority_level = pri_result["priority_level"]
    complaint.priority_score = pri_result["priority_score"]
    _log(db, complaint.id, "priority", "success",
         f"level={pri_result['priority_level']} score={pri_result['priority_score']}")

    complaint.is_processed = True
    return complaint


def run_pipeline(db: Session) -> dict:
    """
    Process all complaints that haven't been analysed yet (is_processed=False).
    Groups them into clusters after individual analysis.

    Returns a summary dict.
    """
    unprocessed: list[Complaint] = (
        db.query(Complaint).filter(Complaint.is_processed == False).all()
    )

    if not unprocessed:
        return {"processed": 0, "clusters_created": 0, "message": "Nothing to process."}

    # Stage 1–2: categorise + sentiment on every complaint
    for c in unprocessed:
        analyse_one(c, db, cluster_size=1)

    db.flush()   # write categories/sentiments without committing

    # Stage 3: cluster ALL processed complaints (not just new ones)
    all_complaints: list[Complaint] = db.query(Complaint).all()
    texts = [c.complaint_text for c in all_complaints]
    cluster_result = cluster_complaints(texts)
    labels = cluster_result["labels"]
    top_terms = cluster_result["top_terms"]

    # Delete old clusters (rebuild from scratch each run)
    db.query(Cluster).delete()
    db.flush()

    # Build Cluster rows
    clusters_map: dict[int, Cluster] = {}
    for cluster_id in range(cluster_result["n_clusters"]):
        members = [all_complaints[i] for i, lbl in enumerate(labels) if lbl == cluster_id]
        avg_sentiment = (
            sum(m.sentiment_score or 0 for m in members) / len(members)
            if members else 0.0
        )
        avg_priority = (
            sum(m.priority_score or 0 for m in members) / len(members)
            if members else 0.0
        )

        # Use the category of the majority of members
        cat_counts: dict[str, int] = {}
        for m in members:
            cat_counts[m.category or "other"] = cat_counts.get(m.category or "other", 0) + 1
        dominant_cat = max(cat_counts, key=lambda c: cat_counts[c])

        label = build_cluster_label(top_terms.get(cluster_id, []), dominant_cat)

        cluster = Cluster(
            id=cluster_id,
            label=label,
            category=dominant_cat,
            complaint_count=len(members),
            avg_sentiment_score=round(avg_sentiment, 4),
            avg_priority_score=round(avg_priority, 2),
        )
        db.add(cluster)
        clusters_map[cluster_id] = cluster

    db.flush()

    # Assign cluster_id back to each complaint; re-score priority with cluster size
    for i, complaint in enumerate(all_complaints):
        cluster_id = labels[i]
        complaint.cluster_id = cluster_id
        size = cluster_result["sizes"].get(cluster_id, 1)

        # Re-score priority now that cluster size is known
        pri_result = calculate_priority(
            complaint_text=complaint.complaint_text,
            sentiment_polarity=complaint.sentiment_score or 0.0,
            category=complaint.category or "other",
            cluster_size=size,
        )
        complaint.priority_level = pri_result["priority_level"]
        complaint.priority_score = pri_result["priority_score"]

    db.commit()

    return {
        "processed": len(unprocessed),
        "clusters_created": cluster_result["n_clusters"],
        "message": (
            f"Processed {len(unprocessed)} complaint(s) into "
            f"{cluster_result['n_clusters']} cluster(s)."
        ),
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _log(db: Session, complaint_id: int, step: str, status: str, detail: str):
    entry = ProcessingLog(
        complaint_id=complaint_id,
        step=step,
        status=status,
        detail=detail,
    )
    db.add(entry)
