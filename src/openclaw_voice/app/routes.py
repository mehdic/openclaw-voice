"""Flask route registration for OpenClaw Voice."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from flask import Flask, g, jsonify, request, session
from livekit import api

from .auth import is_authenticated, login_required
from .config import get_agent_config, get_allowed_models, get_config, get_user_config

DEMO_EMAIL = "demo@example.com"
DEMO_NAME = "Demo User"

logger = logging.getLogger(__name__)


def _sanitize_identity(email: str) -> str:
    """Build a LiveKit-safe participant identity."""

    source = email or "user"
    return "user-" + "".join(char if char.isalnum() else "-" for char in source.lower())


def _command_response(message: str, **extra: Any) -> dict[str, Any]:
    """Build a standard command response payload."""

    payload: dict[str, Any] = {"ok": True, "message": message}
    payload.update(extra)
    return payload


def _session_user() -> dict[str, str]:
    """Return the active session user, including demo defaults."""

    cfg = get_config()
    email = session.get("email") or (DEMO_EMAIL if cfg.auth_mode == "demo" else "")
    name = session.get("name") or (DEMO_NAME if cfg.auth_mode == "demo" else email)
    picture = session.get("picture") or ""
    return {"email": email, "name": name, "picture": picture}


def _agent_payload(agent_id: str) -> dict[str, Any]:
    """Return serialized agent info for the frontend."""

    agent_cfg = get_agent_config(agent_id)
    models = get_allowed_models(agent_id)
    return {
        "id": agent_id,
        "displayName": agent_cfg.display_name or agent_id,
        "emoji": agent_cfg.emoji,
        "language": agent_cfg.language,
        "model": agent_cfg.llm.model,
        "models": models,
    }


def register_routes(app: Flask) -> None:
    """Register API and static routes on the Flask app."""

    cfg = get_config()

    @app.before_request
    def start_request_timer() -> None:
        g.request_started_at = time.perf_counter()

    @app.after_request
    def log_request_timing(response):
        started_at = getattr(g, "request_started_at", None)
        duration_ms = 0.0 if started_at is None else (time.perf_counter() - started_at) * 1000
        logger.info(
            "request_completed method=%s path=%s status=%s duration_ms=%.2f",
            request.method,
            request.path,
            response.status_code,
            duration_ms,
        )
        return response

    @app.get("/health")
    def health():
        return jsonify({"status": "ok", "timestamp": int(time.time())})

    @app.get("/")
    def index():
        return app.send_static_file("index.html")

    @app.get("/api/session")
    def api_session():
        if is_authenticated():
            current_user = _session_user()
            user_cfg = get_user_config(current_user["email"])
            return jsonify(
                {
                    "authenticated": True,
                    "authMode": cfg.auth_mode,
                    "email": current_user["email"],
                    "name": current_user["name"],
                    "picture": current_user["picture"],
                    "googleClientId": cfg.google_client_id,
                    "allowedAgents": user_cfg.agents,
                    "defaultAgent": user_cfg.default,
                    "lastAgent": session.get("last_agent") or user_cfg.default,
                    "modelOverride": session.get("model_override"),
                }
            )
        return jsonify(
            {
                "authenticated": False,
                "authMode": cfg.auth_mode,
                "googleClientId": cfg.google_client_id,
            }
        )

    @app.post("/api/auth/google")
    def api_google_auth():
        if cfg.auth_mode == "demo":
            session.setdefault("email", DEMO_EMAIL)
            session.setdefault("name", DEMO_NAME)
            session.permanent = True
            return jsonify({"ok": True, "email": session["email"], "name": session["name"]})

        if not cfg.google_client_id:
            return jsonify({"error": "Google auth is not configured"}), 500

        from .auth import google_requests, id_token

        body = request.get_json(silent=True) or {}
        credential = body.get("token") or body.get("credential")
        if not credential:
            return jsonify({"error": "Missing Google credential"}), 400

        try:
            info = id_token.verify_oauth2_token(
                credential,
                google_requests.Request(),
                cfg.google_client_id,
            )
        except Exception:
            return jsonify({"error": "Invalid Google token"}), 401

        email = (info.get("email") or "").strip().lower()
        if not info.get("email_verified"):
            return jsonify({"error": "Google email not verified"}), 403
        if email not in cfg.authorized_emails:
            return jsonify({"error": "Access denied"}), 403

        session.clear()
        session.update(
            {
                "email": email,
                "name": info.get("name") or email,
                "picture": info.get("picture") or "",
                "sub": info.get("sub") or "",
            }
        )
        session.permanent = True
        return jsonify({"ok": True, "email": email, "name": session["name"]})

    @app.post("/api/logout")
    def api_logout():
        session.clear()
        return jsonify({"ok": True})

    @app.get("/api/agents")
    @login_required
    def api_agents():
        current_user = _session_user()
        user_cfg = get_user_config(current_user["email"])
        agents = [_agent_payload(agent_id) for agent_id in user_cfg.agents]
        return jsonify(
            {
                "agents": agents,
                "defaultAgent": user_cfg.default,
                "lastAgent": session.get("last_agent") or user_cfg.default,
            }
        )

    @app.get("/api/models")
    @login_required
    def api_models():
        current_user = _session_user()
        user_cfg = get_user_config(current_user["email"])
        agent_id = (request.args.get("agent") or user_cfg.default).lower().strip()
        if agent_id not in user_cfg.agents:
            return jsonify({"error": "Agent not allowed"}), 403
        models = get_allowed_models(agent_id)
        return jsonify(
            {
                "agent": agent_id,
                "current": session.get("model_override") or models[0],
                "primary": models[0],
                "models": models,
            }
        )

    @app.get("/api/token")
    @login_required
    def api_token():
        current_user = _session_user()
        user_cfg = get_user_config(current_user["email"])
        agent_id = (request.args.get("agent") or session.get("last_agent") or user_cfg.default).lower().strip()
        if agent_id not in user_cfg.agents:
            return jsonify({"error": "Agent not allowed"}), 403

        session_id = request.args.get("session") or str(int(time.time()))
        room_name = f"voice-{agent_id}-{session_id}"
        session["last_agent"] = agent_id
        session["last_session_id"] = session_id

        metadata = json.dumps(
            {
                "agent": agent_id,
                "email": current_user["email"],
                "name": current_user["name"],
                "model_override": session.get("model_override"),
            }
        )

        token = (
            api.AccessToken(cfg.livekit_api_key, cfg.livekit_api_secret)
            .with_identity(_sanitize_identity(current_user["email"]))
            .with_name(current_user["name"] or "User")
            .with_grants(
                api.VideoGrants(
                    room_join=True,
                    room=room_name,
                    can_publish=True,
                    can_subscribe=True,
                )
            )
            .with_metadata(metadata)
            .with_room_config(
                api.RoomConfiguration(
                    agents=[
                        api.RoomAgentDispatch(
                            agent_name="openclaw-voice",
                            metadata=metadata,
                        )
                    ],
                )
            )
        )

        return jsonify(
            {
                "serverUrl": cfg.livekit_url,
                "participantToken": token.to_jwt(),
                "room": room_name,
                "agent": agent_id,
                "model": session.get("model_override") or get_allowed_models(agent_id)[0],
                "sessionId": session_id,
            }
        )

    @app.post("/api/command")
    @login_required
    def api_command():
        body = request.get_json(silent=True) or {}
        raw_command = (body.get("command") or "").strip()
        if not raw_command:
            return jsonify({"error": "Missing command"}), 400

        if not raw_command.startswith("/"):
            raw_command = f"/{raw_command}"

        parts = raw_command.split()
        command = parts[0].lower()
        args = body.get("args")
        if args is None:
            args = parts[1:]
        elif isinstance(args, str):
            args = args.split()
        else:
            args = [str(arg).strip() for arg in args if str(arg).strip()]

        current_user = _session_user()
        user_cfg = get_user_config(current_user["email"])
        agent_id = (body.get("agent") or session.get("last_agent") or user_cfg.default).lower().strip()
        if agent_id not in user_cfg.agents:
            agent_id = user_cfg.default

        call_duration = int(body.get("callDuration") or 0)
        minutes, seconds = divmod(max(call_duration, 0), 60)
        current_model = session.get("model_override") or get_allowed_models(agent_id)[0]

        if command == "/help":
            return jsonify(
                _command_response(
                    "Available commands",
                    kind="help",
                    commands=[{"command": key, "description": value} for key, value in cfg.commands.items()],
                )
            )

        if command == "/status":
            return jsonify(
                _command_response(
                    "Current call status",
                    kind="status",
                    status={
                        "agent": agent_id,
                        "model": current_model,
                        "sessionId": session.get("last_session_id") or body.get("sessionId") or "new",
                        "callDuration": f"{minutes:02d}:{seconds:02d}",
                        "connected": bool(body.get("connected", False)),
                        "muted": bool(body.get("isMuted", False)),
                    },
                )
            )

        if command == "/new":
            session["last_agent"] = agent_id
            return jsonify(
                _command_response(
                    "Starting a fresh session",
                    kind="session",
                    client_action={"type": "new_session", "agent": agent_id},
                )
            )

        if command == "/stop":
            return jsonify(
                _command_response(
                    "Ending the current call",
                    kind="session",
                    client_action={"type": "disconnect"},
                )
            )

        if command == "/mute":
            muted = not bool(body.get("isMuted", False))
            return jsonify(
                _command_response(
                    "Microphone muted" if muted else "Microphone unmuted",
                    kind="mute",
                    client_action={"type": "set_mute", "muted": muted},
                )
            )

        if command == "/agent":
            if not args:
                return jsonify(
                    _command_response(
                        "Choose an agent",
                        kind="agents",
                        current=agent_id,
                        buttons=[{"label": value, "value": f"/agent {value}"} for value in user_cfg.agents],
                    )
                )

            new_agent = args[0].lower().strip()
            if new_agent not in user_cfg.agents:
                return jsonify(
                    _command_response(
                        f"Agent '{new_agent}' is not available for this account",
                        kind="error",
                        buttons=[{"label": value, "value": f"/agent {value}"} for value in user_cfg.agents],
                    )
                )

            session["last_agent"] = new_agent
            session.pop("model_override", None)
            return jsonify(
                _command_response(
                    f"Switching to {new_agent}",
                    kind="agent",
                    client_action={"type": "switch_agent", "agent": new_agent},
                )
            )

        if command == "/model":
            allowed_models = get_allowed_models(agent_id)
            if not args:
                current = session.get("model_override") or allowed_models[0]
                return jsonify(
                    _command_response(
                        f"Models for {agent_id}",
                        kind="models",
                        model=current,
                        current=current,
                        buttons=[
                            {"label": model.split("/")[-1], "value": f"/model {model}", "description": model}
                            for model in allowed_models
                        ],
                    )
                )

            requested_model = " ".join(args).strip()
            if requested_model not in allowed_models:
                return jsonify(
                    _command_response(
                        f"Model '{requested_model}' is not allowed for {agent_id}",
                        kind="error",
                        current=current_model,
                        buttons=[
                            {"label": model.split("/")[-1], "value": f"/model {model}", "description": model}
                            for model in allowed_models
                        ],
                    )
                )

            session["model_override"] = None if requested_model == allowed_models[0] else requested_model
            return jsonify(
                _command_response(
                    f"Model set to {requested_model}",
                    kind="model",
                    model=requested_model,
                    client_action={"type": "refresh_call", "agent": agent_id, "model": requested_model},
                )
            )

        return jsonify({"error": f"Unknown command: {command}"}), 400
