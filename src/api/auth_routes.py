"""
Authentication Blueprint
========================
POST  /auth/login   — log in, set session cookie
POST  /auth/logout  — clear session
GET   /auth/me      — return current session info
"""

from flask import Blueprint, request, jsonify, session

from src.db.models import get_db, User
from src.api.auth import check_password

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def _db():
    return next(get_db())


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Body: { "username": "...", "password": "..." }
    Returns: { "role": "...", "username": "...", "full_name": "..." }
    """
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400

    db = _db()
    user = db.query(User).filter_by(username=username).first()

    if not user or not check_password(password, user.password_hash):
        return jsonify({"error": "Invalid credentials"}), 401

    session.clear()
    session["user_id"] = user.id
    session["role"] = user.role
    session["username"] = user.username
    session["full_name"] = user.full_name or user.username

    return jsonify({
        "role": user.role,
        "username": user.username,
        "full_name": user.full_name or user.username,
    }), 200


@auth_bp.route("/logout", methods=["POST"])
def logout():
    """Clear the session."""
    session.clear()
    return jsonify({"message": "Logged out"}), 200


@auth_bp.route("/me", methods=["GET"])
def me():
    """Return the current session's user info."""
    if not session.get("user_id"):
        return jsonify({"error": "Not authenticated"}), 401
    return jsonify({
        "user_id": session["user_id"],
        "role": session["role"],
        "username": session["username"],
        "full_name": session.get("full_name", session["username"]),
    }), 200
