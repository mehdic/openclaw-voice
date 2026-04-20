"""Authentication helpers for the Flask web app."""

from __future__ import annotations

from functools import wraps
from typing import Any

from flask import jsonify, session
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from .config import get_config

__all__ = ["add_security_headers", "google_requests", "id_token", "is_authenticated", "login_required"]


def is_authenticated() -> bool:
    """Check whether the current session is authenticated."""

    cfg = get_config()
    if cfg.auth_mode == "demo":
        return True
    email = (session.get("email") or "").lower()
    return bool(email and email in cfg.authorized_emails)


def login_required(func: Any):
    """Decorator that requires authentication for a route."""

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if not is_authenticated():
            return jsonify({"error": "Not authenticated"}), 401
        return func(*args, **kwargs)

    return wrapper


def add_security_headers(response):
    """Add security headers to all responses."""

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(self), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://accounts.google.com https://*.gstatic.com https://esm.sh https://unpkg.com; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https://*.googleusercontent.com; "
        "frame-src https://accounts.google.com; "
        "connect-src 'self' https://accounts.google.com https://oauth2.googleapis.com "
        "wss: ws: https: http:; "
        "font-src 'self' data:; "
        "media-src 'self' blob:;"
    )
    return response
