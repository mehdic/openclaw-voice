"""Application configuration loading for OpenClaw Voice."""

from __future__ import annotations

import os
import secrets
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONFIG_DIR = PROJECT_ROOT / "config"

DEFAULT_COMMANDS = {
    "/help": "List available voice commands",
    "/status": "Show connection and session status",
    "/agent": "Switch to another allowed agent",
    "/model": "Switch the current agent model",
    "/new": "Start a fresh voice session",
    "/stop": "Disconnect the current call",
    "/mute": "Toggle the microphone",
}


class VoiceSettings(BaseModel):
    """Voice synthesis tuning values."""

    stability: float = 0.5
    similarity_boost: float = 0.75
    style: float = 0.0


class VoiceConfig(BaseModel):
    """Per-agent TTS configuration."""

    provider: str = "elevenlabs"
    voice_id: str
    model: str = "eleven_turbo_v2_5"
    settings: VoiceSettings = Field(default_factory=VoiceSettings)


class LLMModels(BaseModel):
    """Primary and fallback LLM model allowlist."""

    primary: str = ""
    fallbacks: list[str] = Field(default_factory=list)


class LLMConfig(BaseModel):
    """Per-agent LLM configuration."""

    mode: str = "gateway"
    model: str = "anthropic/claude-sonnet-4-6"
    models: LLMModels = Field(default_factory=LLMModels)


class AgentConfig(BaseModel):
    """Agent-level voice configuration."""

    display_name: str = ""
    emoji: str = ""
    voice: VoiceConfig
    llm: LLMConfig = Field(default_factory=LLMConfig)
    language: str = "en"
    tools: list[str] = Field(default_factory=list)


class UserAccess(BaseModel):
    """Per-user allowed agents and default agent."""

    agents: list[str]
    default: str


class TimeoutConfig(BaseModel):
    """HTTP timeout configuration."""

    connect: float = 5.0
    read: float = 30.0
    write: float = 5.0
    pool: float = 5.0


class TimeoutsConfig(BaseModel):
    """Named timeout profiles."""

    gateway: TimeoutConfig = Field(
        default_factory=lambda: TimeoutConfig(connect=10.0, read=90.0, write=10.0, pool=10.0)
    )
    direct: TimeoutConfig = Field(default_factory=TimeoutConfig)
    tools: TimeoutConfig = Field(
        default_factory=lambda: TimeoutConfig(connect=3.0, read=10.0, write=3.0, pool=3.0)
    )


class VoiceDefaults(BaseModel):
    """Global voice defaults."""

    default_model: str = "gpt-5.4-mini"
    default_agent: str = "default"
    stt_model_size: str = "base"
    stt_device: str = "cpu"
    stt_compute_type: str = "int8"
    stt_beam_size: int = 1


class ServerConfig(BaseModel):
    """Web server configuration."""

    web_port: int = 7890
    session_cookie_name: str = "openclaw_voice_session"
    session_cookie_secure: bool = True
    session_cookie_samesite: str = "Strict"


class AppConfig(BaseModel):
    """Top-level application configuration."""

    agents: dict[str, AgentConfig] = Field(default_factory=dict)
    users: dict[str, UserAccess] = Field(default_factory=dict)
    default_user: UserAccess = Field(default_factory=lambda: UserAccess(agents=[], default="default"))
    timeouts: TimeoutsConfig = Field(default_factory=TimeoutsConfig)
    voice: VoiceDefaults = Field(default_factory=VoiceDefaults)
    server: ServerConfig = Field(default_factory=ServerConfig)
    commands: dict[str, str] = Field(default_factory=lambda: dict(DEFAULT_COMMANDS))
    prompts_bootstrap_files: list[str] = Field(default_factory=list)
    prompts_dynamic_files: list[str] = Field(default_factory=list)
    livekit_url: str = ""
    livekit_api_key: str = ""
    livekit_api_secret: str = ""
    openclaw_url: str = ""
    openclaw_token: str = ""
    openai_api_key: str = ""
    google_client_id: str = ""
    authorized_emails: set[str] = Field(default_factory=set)
    session_secret: str = ""
    eleven_api_key: str = ""
    auth_mode: str = "demo"


def _load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML file, returning an empty dict if missing."""

    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _normalize_agent_id(agent_id: str) -> str:
    """Normalize an agent identifier."""

    return agent_id.lower().strip()


def _default_user_access(agent_ids: list[str], default_agent: str) -> UserAccess:
    """Build the fallback user access policy."""

    default = default_agent if default_agent in agent_ids else (agent_ids[0] if agent_ids else default_agent)
    return UserAccess(agents=agent_ids, default=default)


def _load_config() -> AppConfig:
    """Build application config from YAML files and environment variables."""

    defaults = _load_yaml(CONFIG_DIR / "defaults.yaml")
    agents_cfg = _load_yaml(CONFIG_DIR / "agents.yaml")

    agents: dict[str, AgentConfig] = {}
    for agent_id, agent_data in agents_cfg.get("agents", {}).items():
        agents[_normalize_agent_id(agent_id)] = AgentConfig(**agent_data)

    users: dict[str, UserAccess] = {}
    for email, user_data in agents_cfg.get("users", {}).items():
        users[email.lower().strip()] = UserAccess(**user_data)

    voice_data = defaults.get("voice", {})
    voice_defaults = VoiceDefaults(**voice_data)

    default_user_data = agents_cfg.get("default_user")
    default_user = (
        UserAccess(**default_user_data)
        if default_user_data
        else _default_user_access(list(agents.keys()), voice_defaults.default_agent)
    )

    timeouts_data = defaults.get("timeouts", {})
    timeouts = TimeoutsConfig(
        gateway=TimeoutConfig(**timeouts_data.get("gateway", {})),
        direct=TimeoutConfig(**timeouts_data.get("direct", {})),
        tools=TimeoutConfig(**timeouts_data.get("tools", {})),
    )

    server_data = dict(defaults.get("server", {}))
    if os.getenv("WEB_PORT"):
        server_data["web_port"] = int(os.getenv("WEB_PORT", "7890"))
    server = ServerConfig(**server_data)

    prompts_cfg = defaults.get("prompts", {})
    auth_mode = (os.getenv("AUTH_MODE", "demo").strip().lower() or "demo")

    return AppConfig(
        agents=agents,
        users=users,
        default_user=default_user,
        timeouts=timeouts,
        voice=voice_defaults,
        server=server,
        commands=defaults.get("commands", DEFAULT_COMMANDS),
        prompts_bootstrap_files=prompts_cfg.get("bootstrap_files", []),
        prompts_dynamic_files=prompts_cfg.get("dynamic_files", []),
        livekit_url=os.getenv("LIVEKIT_URL", defaults.get("livekit", {}).get("url", "ws://localhost:7880")),
        livekit_api_key=os.getenv("LIVEKIT_API_KEY", ""),
        livekit_api_secret=os.getenv("LIVEKIT_API_SECRET", ""),
        openclaw_url=os.getenv("OPENCLAW_URL", "http://localhost:18789"),
        openclaw_token=os.getenv("OPENCLAW_TOKEN", ""),
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        google_client_id=os.getenv("GOOGLE_CLIENT_ID", ""),
        authorized_emails={email.strip().lower() for email in os.getenv("AUTHORIZED_EMAILS", "").split(",") if email.strip()},
        session_secret=os.getenv("SESSION_SECRET") or secrets.token_hex(32),
        eleven_api_key=os.getenv("ELEVEN_API_KEY", ""),
        auth_mode=auth_mode,
    )


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    """Return the cached application config."""

    return _load_config()


def get_agent_config(agent_id: str) -> AgentConfig:
    """Return config for an agent, falling back to the configured default."""

    cfg = get_config()
    normalized = _normalize_agent_id(agent_id)
    if normalized in cfg.agents:
        return cfg.agents[normalized]
    if cfg.voice.default_agent in cfg.agents:
        return cfg.agents[cfg.voice.default_agent]
    if cfg.agents:
        return next(iter(cfg.agents.values()))
    raise ValueError("No agents configured in config/agents.yaml")


def get_user_config(email: str) -> UserAccess:
    """Return user access configuration for an email."""

    cfg = get_config()
    return cfg.users.get(email.lower().strip(), cfg.default_user)


def get_allowed_models(agent_id: str) -> list[str]:
    """Return allowed models for an agent."""

    agent = get_agent_config(agent_id)
    models = agent.llm.models
    result: list[str] = []
    if models.primary:
        result.append(models.primary)
    result.extend(models.fallbacks)
    return result if result else [agent.llm.model]
