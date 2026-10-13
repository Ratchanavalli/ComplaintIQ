"""
Authentication helpers for the Customer Complaint Intelligence System.

Provides:
  - hash_password / check_password  (werkzeug-backed)
  - login_required / manager_required decorators
  - current_user_id / current_role helpers
"""

from functools import wraps
from flask import session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash


def hash_password(plain: str) -> str:
    """Return a bcrypt/scrypt hash suitable for storage."""
    return generate_password_hash(plain)


def check_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches *hashed*."""
    return check_password_hash(hashed, plain)


def current_user_id() -> int | None:
    """Return the authenticated user's id from the session, or None."""
    return session.get("user_id")


def current_role() -> str:
    """Return the authenticated user's role from the session, or ''."""
    return session.get("role", "")


def login_required(f):
    """Decorator: reject the request with 401 if no session is active."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify({"error": "Authentication required"}), 401
        return f(*args, **kwargs)
    return decorated


def manager_required(f):
    """Decorator: reject with 401 if not logged in, 403 if not a manager."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify({"error": "Authentication required"}), 401
        if session.get("role") != "manager":
            return jsonify({"error": "Manager access required"}), 403
        return f(*args, **kwargs)
    return decorated
