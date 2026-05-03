"""LLM factory for OpenClaw Voice — dispatches by agent mode."""

from __future__ import annotations

from typing import Optional, Union

from livekit.agents.llm import FallbackAdapter
from livekit.plugins import openai

from ..app.config import get_agent_config
from .client import create_codex_proxy_llm, create_gateway_llm

_MODE_CODEX_PROXY = "codex_proxy"


def create_llm(
    agent_id: str,
    model_override: Optional[str] = None,
) -> Union[openai.LLM, FallbackAdapter]:
    """Create an LLM for the requested agent.

    Dispatches to the correct backend based on the agent's ``llm.mode``:

    * ``"gateway"`` (default) — routes through the OpenClaw gateway, uses the
      ``x-openclaw-model`` header to select the model.
    * ``"codex_proxy"`` — same gateway transport but targeted at codex-proxy
      models, and wraps primary + fallbacks in a ``FallbackAdapter`` so LiveKit
      automatically retries with the next model on transient failure.
    """

    agent_cfg = get_agent_config(agent_id)
    mode = agent_cfg.llm.mode if agent_cfg else "gateway"

    if mode == _MODE_CODEX_PROXY:
        return create_codex_proxy_llm(agent_id, model_override)
    return create_gateway_llm(agent_id, model_override)
