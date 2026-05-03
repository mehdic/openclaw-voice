"""Gateway-backed OpenClaw LLM client helpers."""

from __future__ import annotations

from typing import Optional, Union

import httpx
from livekit.agents.llm import FallbackAdapter
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


def _make_gateway_llm_for_model(agent_id: str, model: str, cfg: object) -> openai.LLM:
    """Create a gateway LLM instance pinned to a specific model."""

    return openai.LLM(
        model=f"openclaw/{agent_id}",
        base_url=cfg.openclaw_url.rstrip("/") + "/v1",
        api_key=cfg.openclaw_token or "",
        timeout=httpx.Timeout(**_timeout_kwargs(cfg.timeouts.gateway)),
        extra_headers={"x-openclaw-model": model},
    )


def create_codex_proxy_llm(
    agent_id: str,
    model_override: Optional[str] = None,
) -> Union[openai.LLM, FallbackAdapter]:
    """Create a codex-proxy-backed LLM routed through the OpenClaw gateway.

    When multiple models are configured (primary + fallbacks), wraps them in a
    ``FallbackAdapter`` so LiveKit automatically retries with the next model on
    any transient failure.  With a single model (or an explicit override) a bare
    ``openai.LLM`` is returned so callers don't pay the adapter overhead.

    Model names follow OpenClaw's provider/model convention, e.g.
    ``codex-proxy/gpt-5.5``.  The adapter routes them to the OpenClaw gateway
    via the ``x-openclaw-model`` request header.
    """

    cfg = get_config()
    agent_cfg = cfg.agents.get(agent_id)
    llm_cfg = agent_cfg.llm if agent_cfg else None

    if model_override:
        primary = model_override
        fallback_models: list[str] = []
    elif llm_cfg and llm_cfg.models.primary:
        primary = llm_cfg.models.primary
        fallback_models = list(llm_cfg.models.fallbacks)
    else:
        primary = (llm_cfg.model if llm_cfg else None) or cfg.voice.default_model
        fallback_models = []

    all_models = [primary] + fallback_models
    instances = [_make_gateway_llm_for_model(agent_id, m, cfg) for m in all_models]

    if len(instances) == 1:
        return instances[0]
    return FallbackAdapter(instances)
