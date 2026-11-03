"""Web user interface (Flask)."""
import os

from flask import Flask

from .routes import build_blueprint


def create_app(auth, patients, visits, audit_service) -> Flask:
    """Build the Flask app around already-constructed services."""
    app = Flask(__name__)
    app.secret_key = os.environ.get("PRS_SECRET_KEY", "dev-only-change-me")
    app.register_blueprint(build_blueprint(auth, patients, visits,
                                           audit_service))
    return app
