from __future__ import annotations

from flask import Flask, jsonify, session

from openclaw_voice.app import auth as auth_module


def _make_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = "test-secret"
    return app


def test_is_authenticated_returns_true_in_demo_mode(monkeypatch, test_config):
    app = _make_app()
    test_config.auth_mode = "demo"
    monkeypatch.setattr(auth_module, "get_config", lambda: test_config)

    with app.test_request_context("/"):
        assert auth_module.is_authenticated() is True


def test_is_authenticated_returns_false_when_no_email_in_session_google_mode(monkeypatch, test_config):
    app = _make_app()
    test_config.auth_mode = "google"
    monkeypatch.setattr(auth_module, "get_config", lambda: test_config)

    with app.test_request_context("/"):
        assert auth_module.is_authenticated() is False


def test_is_authenticated_returns_true_when_email_is_authorized_google_mode(monkeypatch, test_config):
    app = _make_app()
    test_config.auth_mode = "google"
    monkeypatch.setattr(auth_module, "get_config", lambda: test_config)

    with app.test_request_context("/"):
        session["email"] = "allowed@example.com"
        assert auth_module.is_authenticated() is True


def test_login_required_blocks_unauthenticated_google_mode(monkeypatch, test_config):
    app = _make_app()
    test_config.auth_mode = "google"
    monkeypatch.setattr(auth_module, "get_config", lambda: test_config)

    @app.get("/protected")
    @auth_module.login_required
    def protected():
        return jsonify({"ok": True})

    response = app.test_client().get("/protected")

    assert response.status_code == 401
    assert response.get_json() == {"error": "Not authenticated"}


def test_login_required_allows_demo_mode(monkeypatch, test_config):
    app = _make_app()
    test_config.auth_mode = "demo"
    monkeypatch.setattr(auth_module, "get_config", lambda: test_config)

    @app.get("/protected")
    @auth_module.login_required
    def protected():
        return jsonify({"ok": True})

    response = app.test_client().get("/protected")

    assert response.status_code == 200
    assert response.get_json() == {"ok": True}
