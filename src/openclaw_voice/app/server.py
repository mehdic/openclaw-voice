"""Flask application factory for OpenClaw Voice."""

from __future__ import annotations

from pathlib import Path

from flask import Flask

from .auth import add_security_headers
from .config import get_config
from .routes import register_routes


def create_app() -> Flask:
    """Create and configure the Flask application."""

    cfg = get_config()
    package_root = Path(__file__).resolve().parents[1]
    web_dir = package_root / "web" / "static"

    app = Flask(
        __name__,
        static_folder=str(web_dir),
        static_url_path="",
    )

    app.secret_key = cfg.session_secret
    app.config.update(
        SESSION_COOKIE_NAME=cfg.server.session_cookie_name,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE=cfg.server.session_cookie_samesite,
        SESSION_COOKIE_SECURE=cfg.server.session_cookie_secure,
    )

    register_routes(app)
    app.after_request(add_security_headers)
    return app
