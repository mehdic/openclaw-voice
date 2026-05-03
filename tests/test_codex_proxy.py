"""Tests for codex-proxy LLM with automatic FallbackAdapter wiring."""

from __future__ import annotations

import pytest

from openclaw_voice.app import config as config_module
from openclaw_voice.openclaw import client as client_module
from openclaw_voice.openclaw import llm as llm_module


class DummyTimeout:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class DummyLLM:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class DummyFallbackAdapter:
    def __init__(self, llm: list, **kwargs):
        self.llm = llm
        self.kwargs = kwargs


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def codex_agent_config():
    """Agent configured with codex_proxy mode, primary + two fallbacks."""
    return config_module.AgentConfig(
        display_name="Sevro",
        emoji="🐺",
        language="en",
        voice=config_module.VoiceConfig(voice_id="voice-sevro"),
        llm=config_module.LLMConfig(
            mode="codex_proxy",
            model="codex-proxy/gpt-5.5",
            models=config_module.LLMModels(
                primary="codex-proxy/gpt-5.5",
                fallbacks=["codex-proxy/gpt-5.4-mini", "codex-proxy/gpt-4o-mini"],
            ),
        ),
    )


@pytest.fixture
def codex_config(codex_agent_config):
    return config_module.AppConfig(
        agents={"sevro": codex_agent_config},
        voice=config_module.VoiceDefaults(default_model="codex-proxy/gpt-5.5", default_agent="sevro"),
        openclaw_url="https://openclaw.example.test/",
        openclaw_token="test-token",
    )


@pytest.fixture(autouse=True)
def patch_livekit(monkeypatch):
    monkeypatch.setattr(client_module.httpx, "Timeout", DummyTimeout)
    monkeypatch.setattr(client_module.openai, "LLM", DummyLLM)
    monkeypatch.setattr(client_module, "FallbackAdapter", DummyFallbackAdapter)


# ---------------------------------------------------------------------------
# create_codex_proxy_llm — model selection
# ---------------------------------------------------------------------------


def test_codex_proxy_uses_primary_model(monkeypatch, codex_config):
    monkeypatch.setattr(client_module, "get_config", lambda: codex_config)

    result = client_module.create_codex_proxy_llm("sevro")

    assert isinstance(result, DummyFallbackAdapter)
    # First LLM in the adapter is the primary
    primary_llm = result.llm[0]
    assert primary_llm.kwargs["extra_headers"] == {"x-openclaw-model": "codex-proxy/gpt-5.5"}


def test_codex_proxy_includes_all_fallback_models(monkeypatch, codex_config):
    monkeypatch.setattr(client_module, "get_config", lambda: codex_config)

    result = client_module.create_codex_proxy_llm("sevro")

    assert isinstance(result, DummyFallbackAdapter)
    models_used = [llm.kwargs["extra_headers"]["x-openclaw-model"] for llm in result.llm]
    assert models_used == [
        "codex-proxy/gpt-5.5",
        "codex-proxy/gpt-5.4-mini",
        "codex-proxy/gpt-4o-mini",
    ]


def test_codex_proxy_model_override_bypasses_fallbacks(monkeypatch, codex_config):
    """An explicit model_override pins a single model — no FallbackAdapter needed."""
    monkeypatch.setattr(client_module, "get_config", lambda: codex_config)

    result = client_module.create_codex_proxy_llm("sevro", model_override="codex-proxy/gpt-5.4-mini")

    # Single model → bare LLM, not FallbackAdapter
    assert isinstance(result, DummyLLM)
    assert result.kwargs["extra_headers"] == {"x-openclaw-model": "codex-proxy/gpt-5.4-mini"}


def test_codex_proxy_no_fallbacks_returns_bare_llm(monkeypatch):
    """When no fallbacks are configured a bare LLM is returned (no adapter overhead)."""
    cfg = config_module.AppConfig(
        agents={
            "sevro": config_module.AgentConfig(
                display_name="Sevro",
                emoji="🐺",
                language="en",
                voice=config_module.VoiceConfig(voice_id="v"),
                llm=config_module.LLMConfig(
                    mode="codex_proxy",
                    model="codex-proxy/gpt-5.5",
                    models=config_module.LLMModels(primary="codex-proxy/gpt-5.5"),
                ),
            )
        },
        voice=config_module.VoiceDefaults(default_model="codex-proxy/gpt-5.5", default_agent="sevro"),
        openclaw_url="https://openclaw.example.test/",
    )
    monkeypatch.setattr(client_module, "get_config", lambda: cfg)

    result = client_module.create_codex_proxy_llm("sevro")

    assert isinstance(result, DummyLLM)
    assert result.kwargs["extra_headers"] == {"x-openclaw-model": "codex-proxy/gpt-5.5"}


def test_codex_proxy_falls_back_to_default_model_when_unconfigured(monkeypatch):
    """Agent with no models block falls back to voice.default_model."""
    cfg = config_module.AppConfig(
        agents={
            "sevro": config_module.AgentConfig(
                display_name="Sevro",
                emoji="🐺",
                language="en",
                voice=config_module.VoiceConfig(voice_id="v"),
                llm=config_module.LLMConfig(mode="codex_proxy", model="codex-proxy/gpt-5.5"),
            )
        },
        voice=config_module.VoiceDefaults(default_model="codex-proxy/gpt-5.5", default_agent="sevro"),
        openclaw_url="https://openclaw.example.test/",
    )
    monkeypatch.setattr(client_module, "get_config", lambda: cfg)

    result = client_module.create_codex_proxy_llm("sevro")

    # model field is the fallback, no fallbacks list → bare LLM
    assert isinstance(result, DummyLLM)
    assert result.kwargs["extra_headers"] == {"x-openclaw-model": "codex-proxy/gpt-5.5"}


# ---------------------------------------------------------------------------
# create_codex_proxy_llm — gateway routing
# ---------------------------------------------------------------------------


def test_codex_proxy_routes_through_gateway(monkeypatch, codex_config):
    monkeypatch.setattr(client_module, "get_config", lambda: codex_config)

    result = client_module.create_codex_proxy_llm("sevro")

    for llm in result.llm:
        assert llm.kwargs["base_url"] == "https://openclaw.example.test/v1"
        assert llm.kwargs["api_key"] == "test-token"
        assert llm.kwargs["model"] == "openclaw/sevro"


def test_codex_proxy_fallback_adapter_receives_all_instances(monkeypatch, codex_config):
    monkeypatch.setattr(client_module, "get_config", lambda: codex_config)

    result = client_module.create_codex_proxy_llm("sevro")

    assert isinstance(result, DummyFallbackAdapter)
    assert len(result.llm) == 3  # primary + 2 fallbacks


# ---------------------------------------------------------------------------
# create_llm dispatch — mode routing
# ---------------------------------------------------------------------------


def test_create_llm_dispatches_codex_proxy_mode(monkeypatch, codex_config):
    monkeypatch.setattr(config_module, "get_config", lambda: codex_config)
    monkeypatch.setattr(client_module, "get_config", lambda: codex_config)

    result = llm_module.create_llm("sevro")

    assert isinstance(result, DummyFallbackAdapter)


def test_create_llm_dispatches_gateway_mode(monkeypatch, test_config):
    monkeypatch.setattr(config_module, "get_config", lambda: test_config)
    monkeypatch.setattr(client_module, "get_config", lambda: test_config)

    result = llm_module.create_llm("test-agent")

    assert isinstance(result, DummyLLM)
    assert result.kwargs["model"] == "openclaw/test-agent"


def test_create_llm_codex_proxy_with_model_override_returns_bare_llm(monkeypatch, codex_config):
    monkeypatch.setattr(config_module, "get_config", lambda: codex_config)
    monkeypatch.setattr(client_module, "get_config", lambda: codex_config)

    result = llm_module.create_llm("sevro", model_override="codex-proxy/gpt-5.4-mini")

    assert isinstance(result, DummyLLM)
    assert result.kwargs["extra_headers"] == {"x-openclaw-model": "codex-proxy/gpt-5.4-mini"}


# ---------------------------------------------------------------------------
# Fallback ordering — primary is always first
# ---------------------------------------------------------------------------


def test_fallback_order_is_primary_then_fallbacks(monkeypatch, codex_config):
    monkeypatch.setattr(client_module, "get_config", lambda: codex_config)

    result = client_module.create_codex_proxy_llm("sevro")

    headers = [llm.kwargs["extra_headers"]["x-openclaw-model"] for llm in result.llm]
    assert headers[0] == "codex-proxy/gpt-5.5", "Primary must be first in the adapter list"
    assert headers[1] == "codex-proxy/gpt-5.4-mini"
    assert headers[2] == "codex-proxy/gpt-4o-mini"
