import os
from flask import Flask, send_from_directory
from flask_cors import CORS

from .routes import api_bp
from .auth_routes import auth_bp

# Resolve the static folder relative to this file
_STATIC = os.path.join(os.path.dirname(__file__), "..", "..", "static")


def create_app() -> Flask:
    app = Flask(__name__, static_folder=os.path.abspath(_STATIC))
    CORS(app, supports_credentials=True)

    # Session cookie configuration
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    # Register blueprints
    app.register_blueprint(api_bp)
    app.register_blueprint(auth_bp)

    @app.route("/")
    def dashboard():
        return send_from_directory(app.static_folder, "index.html")

    @app.route("/customer")
    def customer_portal():
        return send_from_directory(app.static_folder, "customer.html")

    @app.route("/management")
    def management_portal():
        return send_from_directory(app.static_folder, "management.html")

    @app.route("/health")
    def health():
        return {"status": "ok", "service": "complaint-intelligence-api"}

    return app
