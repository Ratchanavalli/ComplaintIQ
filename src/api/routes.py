"""
Flask REST API
==============
Endpoints
---------
POST   /api/complaints                          Submit a new complaint (login required)
GET    /api/complaints                          List all complaints (public)
GET    /api/complaints/summary                  High-level counts & stats (public)
GET    /api/complaints/clusters                 All clusters (public)
GET    /api/complaints/priority                 Complaints sorted by priority (public)
GET    /api/complaints/alerts                   Early-warning alerts (manager)
GET    /api/complaints/trends                   14-day / category trends (manager)
GET    /api/complaints/<id>/detail              Full detail incl. responses (login required)
GET    /api/complaints/<id>/responses           Customer-visible responses (login required)
GET    /api/complaints/<id>/similar             Similar complaints in same cluster (manager)
GET    /api/complaints/<id>/priority-explanation Priority breakdown (login required)
POST   /api/complaints/<id>/respond             Add manager response (manager)
POST   /api/complaints/<id>/note               Add internal note (manager)
PATCH  /api/complaints/<id>/status             Update status (manager)
POST   /api/complaints/run-pipeline             Reprocess unanalysed complaints
"""

from datetime import datetime, timedelta, timezone

from flask import Blueprint, request, jsonify, abort

from src.db.models import Complaint, Cluster, ComplaintResponse, InternalNote, User, get_db
from src.utils.pipeline import run_pipeline, analyse_one
from src.api.auth import (
    login_required, manager_required,
    current_user_id, current_role,
)
from src.priority.scorer import calculate_priority

api_bp = Blueprint("api", __name__, url_prefix="/api")


def _db():
    """Return the next db session from the generator."""
    return next(get_db())


# ── Submit a complaint ────────────────────────────────────────────────────────

@api_bp.route("/complaints", methods=["POST"])
@login_required
def submit_complaint():
    """
    Body (JSON) — customer_id is taken from session; complaint_text is required.
    Optional: customer_name, email, channel, product_id, order_id.
    """
    data = request.get_json(silent=True)
    if not data:
        abort(400, "JSON body required.")

    if not data.get("complaint_text"):
        abort(400, "Missing required field: complaint_text")

    db = _db()
    # Use the authenticated user's id as customer_id
    cust_id = str(current_user_id())

    complaint = Complaint(
        customer_id=cust_id,
        customer_name=data.get("customer_name"),
        email=data.get("email"),
        complaint_text=data["complaint_text"],
        channel=data.get("channel"),
        product_id=data.get("product_id"),
        order_id=data.get("order_id"),
        status="open",
    )
    db.add(complaint)
    db.flush()  # get the id

    # Run all 4 analysis stages immediately
    analyse_one(complaint, db)
    db.commit()

    return jsonify(_complaint_dict(complaint)), 201


# ── List complaints ───────────────────────────────────────────────────────────

@api_bp.route("/complaints", methods=["GET"])
def list_complaints():
    """
    Query params: category, sentiment, priority, sort, order, limit, offset.
    Customers see only their own complaints.
    """
    db = _db()
    q = db.query(Complaint)

    # Customers can only see their own complaints
    role = current_role()
    uid = current_user_id()
    if role == "customer" and uid is not None:
        q = q.filter(Complaint.customer_id == str(uid))

    category  = request.args.get("category")
    sentiment = request.args.get("sentiment")
    priority  = request.args.get("priority")

    if category:
        q = q.filter(Complaint.category == category)
    if sentiment:
        q = q.filter(Complaint.sentiment == sentiment)
    if priority:
        q = q.filter(Complaint.priority_level == priority)

    sort_field = request.args.get("sort", "priority_score")
    order = request.args.get("order", "desc")
    col = getattr(Complaint, sort_field, Complaint.priority_score)
    q = q.order_by(col.desc() if order == "desc" else col.asc())

    limit  = min(int(request.args.get("limit", 50)), 200)
    offset = int(request.args.get("offset", 0))
    total  = q.count()
    items  = q.offset(offset).limit(limit).all()

    return jsonify({
        "total": total,
        "limit": limit,
        "offset": offset,
        "results": [_complaint_dict(c) for c in items],
    })


# ── Get one complaint ─────────────────────────────────────────────────────────

@api_bp.route("/complaints/<int:complaint_id>", methods=["GET"])
def get_complaint(complaint_id: int):
    db = _db()
    complaint = db.get(Complaint, complaint_id)
    if not complaint:
        abort(404, f"Complaint {complaint_id} not found.")
    return jsonify(_complaint_dict(complaint))


# ── Summary stats ─────────────────────────────────────────────────────────────

@api_bp.route("/complaints/summary", methods=["GET"])
def summary():
    db = _db()
    complaints = db.query(Complaint).all()

    total = len(complaints)
    by_category: dict[str, int] = {}
    by_sentiment: dict[str, int] = {}
    by_priority: dict[str, int] = {}

    for c in complaints:
        by_category[c.category or "unknown"] = by_category.get(c.category or "unknown", 0) + 1
        by_sentiment[c.sentiment or "unknown"] = by_sentiment.get(c.sentiment or "unknown", 0) + 1
        by_priority[c.priority_level or "unknown"] = by_priority.get(c.priority_level or "unknown", 0) + 1

    avg_priority_score = (
        sum(c.priority_score or 0 for c in complaints) / total if total else 0
    )

    return jsonify({
        "total_complaints": total,
        "by_category": by_category,
        "by_sentiment": by_sentiment,
        "by_priority_level": by_priority,
        "avg_priority_score": round(avg_priority_score, 2),
    })


# ── Clusters ──────────────────────────────────────────────────────────────────

@api_bp.route("/complaints/clusters", methods=["GET"])
def list_clusters():
    db = _db()
    clusters = db.query(Cluster).order_by(Cluster.avg_priority_score.desc()).all()
    return jsonify([_cluster_dict(cl) for cl in clusters])


# ── Priority view ─────────────────────────────────────────────────────────────

@api_bp.route("/complaints/priority", methods=["GET"])
def priority_list():
    """Returns complaints sorted by priority score, highest first."""
    db = _db()
    complaints = (
        db.query(Complaint)
        .order_by(Complaint.priority_score.desc())
        .limit(50)
        .all()
    )
    return jsonify([_complaint_dict(c) for c in complaints])


# ── Early-warning alerts  (MUST be before /<int:complaint_id> routes) ─────────

@api_bp.route("/complaints/alerts", methods=["GET"])
@manager_required
def alerts():
    """
    Early-warning signals:
      - volume_alerts : categories with a recent spike (last 7d vs prior 7d)
      - cluster_alerts: clusters whose avg_priority_score > 75
      - critical_recent: critical complaints in the last 48 h
    Uses pure SQLAlchemy — no pandas.
    """
    db = _db()
    now = datetime.utcnow()
    cutoff_recent = now - timedelta(days=7)
    cutoff_prior  = now - timedelta(days=14)
    cutoff_48h    = now - timedelta(hours=48)

    # ── Count by category in recent vs prior window ───────────────────────────
    recent_complaints = db.query(Complaint).filter(
        Complaint.submitted_at >= cutoff_recent
    ).all()
    prior_complaints = db.query(Complaint).filter(
        Complaint.submitted_at >= cutoff_prior,
        Complaint.submitted_at < cutoff_recent,
    ).all()

    recent_counts: dict[str, int] = {}
    for c in recent_complaints:
        key = c.category or "unknown"
        recent_counts[key] = recent_counts.get(key, 0) + 1

    prior_counts: dict[str, int] = {}
    for c in prior_complaints:
        key = c.category or "unknown"
        prior_counts[key] = prior_counts.get(key, 0) + 1

    all_categories = set(recent_counts) | set(prior_counts)
    volume_alerts = []
    for cat in all_categories:
        recent = recent_counts.get(cat, 0)
        prior  = prior_counts.get(cat, 0)
        if (prior == 0 and recent >= 3) or (prior > 0 and recent > 2 * prior):
            volume_alerts.append({
                "category": cat,
                "recent_count": recent,
                "prior_count": prior,
            })

    # ── High-priority clusters ────────────────────────────────────────────────
    hot_clusters = db.query(Cluster).filter(
        Cluster.avg_priority_score > 75
    ).all()
    cluster_alerts = [_cluster_dict(cl) for cl in hot_clusters]

    # ── Critical complaints in last 48 h ──────────────────────────────────────
    critical_recent = db.query(Complaint).filter(
        Complaint.priority_level == "critical",
        Complaint.submitted_at >= cutoff_48h,
    ).order_by(Complaint.priority_score.desc()).all()

    return jsonify({
        "volume_alerts": volume_alerts,
        "cluster_alerts": cluster_alerts,
        "critical_recent": [_complaint_dict(c) for c in critical_recent],
    })


# ── Trends  (also before /<int:complaint_id>) ─────────────────────────────────

@api_bp.route("/complaints/trends", methods=["GET"])
@manager_required
def trends():
    """
    Returns:
      - daily_counts : last 14 days — [{date, count}]
      - by_category  : last 7 days  — [{category, count}]
    Pure SQLAlchemy, no pandas.
    """
    db = _db()
    now = datetime.utcnow()

    # ── Daily counts for last 14 days ─────────────────────────────────────────
    daily_counts = []
    for days_ago in range(13, -1, -1):
        day_start = (now - timedelta(days=days_ago)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        day_end = day_start + timedelta(days=1)
        count = db.query(Complaint).filter(
            Complaint.submitted_at >= day_start,
            Complaint.submitted_at < day_end,
        ).count()
        daily_counts.append({
            "date": day_start.strftime("%Y-%m-%d"),
            "count": count,
        })

    # ── By category for last 7 days ───────────────────────────────────────────
    cutoff_7d = now - timedelta(days=7)
    recent = db.query(Complaint).filter(
        Complaint.submitted_at >= cutoff_7d
    ).all()

    cat_counts: dict[str, int] = {}
    for c in recent:
        key = c.category or "unknown"
        cat_counts[key] = cat_counts.get(key, 0) + 1

    by_category = [
        {"category": cat, "count": cnt}
        for cat, cnt in sorted(cat_counts.items(), key=lambda x: -x[1])
    ]

    return jsonify({
        "daily_counts": daily_counts,
        "by_category": by_category,
    })


# ── Complaint detail (full, incl. responses) ──────────────────────────────────

@api_bp.route("/complaints/<int:complaint_id>/detail", methods=["GET"])
@login_required
def complaint_detail(complaint_id: int):
    """Full detail including customer-visible responses."""
    db = _db()
    complaint = db.get(Complaint, complaint_id)
    if not complaint:
        abort(404, f"Complaint {complaint_id} not found.")

    role = current_role()
    uid  = current_user_id()
    if role == "customer" and str(complaint.customer_id) != str(uid):
        return jsonify({"error": "Access denied"}), 403

    # Responses: customers see only visible ones
    all_responses = complaint.responses.all()
    if role == "customer":
        all_responses = [r for r in all_responses if r.is_visible_to_customer]

    detail = _complaint_dict(complaint)
    detail["responses"] = [_response_dict(r) for r in all_responses]
    detail["status"] = complaint.status
    detail["assigned_to"] = complaint.assigned_to
    detail["resolution_notes"] = complaint.resolution_notes
    detail["resolved_at"] = complaint.resolved_at.isoformat() if complaint.resolved_at else None

    return jsonify(detail)


# ── Customer-visible responses ────────────────────────────────────────────────

@api_bp.route("/complaints/<int:complaint_id>/responses", methods=["GET"])
@login_required
def complaint_responses(complaint_id: int):
    db = _db()
    complaint = db.get(Complaint, complaint_id)
    if not complaint:
        abort(404, f"Complaint {complaint_id} not found.")

    role = current_role()
    uid  = current_user_id()
    if role == "customer" and str(complaint.customer_id) != str(uid):
        return jsonify({"error": "Access denied"}), 403

    all_responses = complaint.responses.all()
    if role == "customer":
        all_responses = [r for r in all_responses if r.is_visible_to_customer]

    return jsonify([_response_dict(r) for r in all_responses])


# ── Add manager response ──────────────────────────────────────────────────────

@api_bp.route("/complaints/<int:complaint_id>/respond", methods=["POST"])
@manager_required
def add_response(complaint_id: int):
    """Body: { "response_text": "..." }"""
    db = _db()
    complaint = db.get(Complaint, complaint_id)
    if not complaint:
        abort(404, f"Complaint {complaint_id} not found.")

    data = request.get_json(silent=True) or {}
    response_text = data.get("response_text", "").strip()
    if not response_text:
        abort(400, "response_text is required.")

    resp = ComplaintResponse(
        complaint_id=complaint_id,
        manager_id=current_user_id(),
        response_text=response_text,
        is_visible_to_customer=True,
    )
    db.add(resp)

    if complaint.status == "open":
        complaint.status = "in_progress"

    db.commit()
    return jsonify(_response_dict(resp)), 201


# ── Add internal note ─────────────────────────────────────────────────────────

@api_bp.route("/complaints/<int:complaint_id>/note", methods=["POST"])
@manager_required
def add_note(complaint_id: int):
    """Body: { "note_text": "..." }"""
    db = _db()
    complaint = db.get(Complaint, complaint_id)
    if not complaint:
        abort(404, f"Complaint {complaint_id} not found.")

    data = request.get_json(silent=True) or {}
    note_text = data.get("note_text", "").strip()
    if not note_text:
        abort(400, "note_text is required.")

    note = InternalNote(
        complaint_id=complaint_id,
        manager_id=current_user_id(),
        note_text=note_text,
    )
    db.add(note)
    db.commit()
    return jsonify(_note_dict(note)), 201


# ── Update complaint status ───────────────────────────────────────────────────

@api_bp.route("/complaints/<int:complaint_id>/status", methods=["PATCH"])
@manager_required
def update_status(complaint_id: int):
    """Body: { "status": "open|in_progress|resolved|closed" }"""
    db = _db()
    complaint = db.get(Complaint, complaint_id)
    if not complaint:
        abort(404, f"Complaint {complaint_id} not found.")

    data = request.get_json(silent=True) or {}
    new_status = data.get("status", "").strip()
    valid_statuses = {"open", "in_progress", "resolved", "closed"}
    if new_status not in valid_statuses:
        abort(400, f"Invalid status. Must be one of: {', '.join(valid_statuses)}")

    complaint.status = new_status
    if new_status == "resolved":
        complaint.resolved_at = datetime.utcnow()

    db.commit()
    return jsonify(_complaint_dict(complaint))


# ── Similar complaints ────────────────────────────────────────────────────────

@api_bp.route("/complaints/<int:complaint_id>/similar", methods=["GET"])
@manager_required
def similar_complaints(complaint_id: int):
    """Top-5 complaints in the same cluster, sorted by priority_score DESC."""
    db = _db()
    complaint = db.get(Complaint, complaint_id)
    if not complaint:
        abort(404, f"Complaint {complaint_id} not found.")

    if complaint.cluster_id is None:
        return jsonify([])

    similar = (
        db.query(Complaint)
        .filter(
            Complaint.cluster_id == complaint.cluster_id,
            Complaint.id != complaint_id,
        )
        .order_by(Complaint.priority_score.desc())
        .limit(5)
        .all()
    )
    return jsonify([_complaint_dict(c) for c in similar])


# ── Priority explanation ──────────────────────────────────────────────────────

@api_bp.route("/complaints/<int:complaint_id>/priority-explanation", methods=["GET"])
@login_required
def priority_explanation(complaint_id: int):
    """
    Recalculate priority breakdown and return human-readable explanation.
    Customers can only explain their own complaints.
    """
    db = _db()
    complaint = db.get(Complaint, complaint_id)
    if not complaint:
        abort(404, f"Complaint {complaint_id} not found.")

    role = current_role()
    uid  = current_user_id()
    if role == "customer" and str(complaint.customer_id) != str(uid):
        return jsonify({"error": "Access denied"}), 403

    cluster_size = 1
    if complaint.cluster_id is not None:
        cluster = db.get(Cluster, complaint.cluster_id)
        if cluster:
            cluster_size = cluster.complaint_count or 1

    result = calculate_priority(
        complaint_text=complaint.complaint_text,
        sentiment_polarity=complaint.sentiment_score or 0.0,
        category=complaint.category or "other",
        cluster_size=cluster_size,
    )
    breakdown = result["breakdown"]

    explanation = (
        f"This complaint received a priority score of {result['priority_score']:.1f}/100 "
        f"({result['priority_level'].upper()}).\n\n"
        f"• Sentiment: {breakdown['sentiment_pts']:.1f} pts — "
        f"({'negative tone detected' if breakdown['sentiment_pts'] > 20 else 'neutral/positive tone'}).\n"
        f"• Category '{complaint.category or 'other'}': {breakdown['category_pts']:.1f} pts — "
        f"base weight for this complaint type.\n"
        f"• Urgency keywords: {breakdown['urgency_pts']:.1f} pts — "
        f"{'high-urgency language found in the complaint text' if breakdown['urgency_pts'] > 0 else 'no urgency keywords detected'}.\n"
        f"• Cluster size ({cluster_size} complaints): {breakdown['cluster_pts']:.1f} pts — "
        f"{'systemic issue signal' if breakdown['cluster_pts'] > 5 else 'isolated complaint'}."
    )

    return jsonify({
        "complaint_id": complaint_id,
        "priority_score": result["priority_score"],
        "priority_level": result["priority_level"],
        "explanation": explanation,
        "breakdown": breakdown,
    })


# ── Run pipeline manually ─────────────────────────────────────────────────────

@api_bp.route("/complaints/run-pipeline", methods=["POST"])
def trigger_pipeline():
    """Re-runs the full pipeline on any unprocessed complaints."""
    db = _db()
    result = run_pipeline(db)
    return jsonify(result)


# ── Serialisers ───────────────────────────────────────────────────────────────

def _complaint_dict(c: Complaint) -> dict:
    return {
        "id": c.id,
        "customer_id": c.customer_id,
        "customer_name": c.customer_name,
        "email": c.email,
        "complaint_text": c.complaint_text,
        "channel": c.channel,
        "product_id": c.product_id,
        "order_id": c.order_id,
        "submitted_at": c.submitted_at.isoformat() if c.submitted_at else None,
        "category": c.category,
        "sentiment": c.sentiment,
        "sentiment_score": c.sentiment_score,
        "priority_level": c.priority_level,
        "priority_score": c.priority_score,
        "cluster_id": c.cluster_id,
        "is_processed": c.is_processed,
        "status": c.status,
        "assigned_to": c.assigned_to,
        "resolution_notes": c.resolution_notes,
        "resolved_at": c.resolved_at.isoformat() if c.resolved_at else None,
    }


def _response_dict(r: ComplaintResponse) -> dict:
    return {
        "id": r.id,
        "complaint_id": r.complaint_id,
        "manager_id": r.manager_id,
        "response_text": r.response_text,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "is_visible_to_customer": r.is_visible_to_customer,
    }


def _note_dict(n: InternalNote) -> dict:
    return {
        "id": n.id,
        "complaint_id": n.complaint_id,
        "manager_id": n.manager_id,
        "note_text": n.note_text,
        "created_at": n.created_at.isoformat() if n.created_at else None,
    }


def _cluster_dict(cl: Cluster) -> dict:
    return {
        "id": cl.id,
        "label": cl.label,
        "category": cl.category,
        "complaint_count": cl.complaint_count,
        "avg_sentiment_score": cl.avg_sentiment_score,
        "avg_priority_score": cl.avg_priority_score,
    }
