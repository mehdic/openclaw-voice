"""Gateway-backed OpenClaw LLM client helpers."""

from __future__ import annotations

from typing import Optional

import httpx
from livekit.plugins import openai

from ..app.config import get_config


def _timeout_kwargs(timeout_config: object) -> dict:
    """Serialize timeout config for httpx."""

    for attr in ("model_dump", "dict"):
        method = getattr(timeout_config, attr, None)
        if callable(method):
            value = method()
            if isinstance(value, dict):
                return value
    return {
        "connect": timeout_config.connect,
        "read": timeout_config.read,
        "write": timeout_config.write,
        "pool": timeout_config.pool,
    }


def create_gateway_llm(agent_id: str, model_override: Optional[str] = None) -> openai.LLM:
    """Create an OpenClaw gateway-backed LLM instance."""

    cfg = get_config()
    agent_cfg = cfg.agents.get(agent_id)
    agent_model = agent_cfg.llm.model if agent_cfg else None
    effective_model = model_override or agent_model or cfg.voice.default_model
    return openai.LLM(
        model=f"openclaw/{agent_id}",
        base_url=cfg.openclaw_url.rstrip("/") + "/v1",
        api_key=cfg.openclaw_token or "",
        timeout=httpx.Timeout(**_timeout_kwargs(cfg.timeouts.gateway)),
        extra_headers={"x-openclaw-model": effective_model},
    )
