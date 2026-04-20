"""Gateway-only LLM factory for OpenClaw Voice."""

from __future__ import annotations

from typing import Optional

from livekit.plugins import openai

from .client import create_gateway_llm


def create_llm(agent_id: str, model_override: Optional[str] = None) -> openai.LLM:
    """Create an LLM for the requested agent."""

    return create_gateway_llm(agent_id, model_override)
